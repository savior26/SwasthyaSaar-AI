from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from typing import Optional, TypedDict
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from models.patient_summary_session_model import PatientSummarySession
from schemas.patient_summary_schema import (
    PatientInformation,
    PatientSymptomReport,
    PatientSummaryResponse,
)
from services.ai_model import ai_Model


class InterviewTurn(BaseModel):
    question: Optional[str] = None
    completed: bool = False
    report: Optional[PatientSymptomReport] = None


class EmergencyScreen(BaseModel):
    emergency: bool
    reason: str = ""


class InterviewState(TypedDict, total=False):
    patient_id: str
    patient: dict
    conversation: list[dict[str, str]]
    user_turns: int
    question: Optional[str]
    completed: bool
    emergency: bool
    emergency_message: Optional[str]
    report: Optional[dict]


class PatientSummarySessionNotFound(LookupError):
    pass


INTERVIEW_INSTRUCTIONS = """
You are a compassionate clinical intake assistant preparing a patient's
reported symptom history for a clinician. You are not a doctor.

Ask exactly one short, plain-language question in each reply. Collect the
patient's main concern, onset and duration, location, character, severity,
frequency, associated or explicitly denied symptoms, triggers or relief, and
relevant medical history, medicines, and allergies when appropriate. Do not
repeat questions already answered. Use the patient's language.

Do not diagnose, recommend treatment, or invent facts. Do not call a symptom
absent unless the patient explicitly denies it. Do not claim a safety screen
proves the patient is safe.

When the patient explicitly asks to finish, or after enough information has
been collected (usually 3-5 patient answers), set completed=true and provide
a structured doctor-ready report. If more essential information is needed,
set completed=false and ask the next single question.

If completed=true, report must be present and accurately organize only facts
from the conversation and supplied patient profile. If completed=false, report
must be null.
"""

EMERGENCY_INSTRUCTIONS = """
You are an urgent-symptom screening assistant, not a diagnostic system.
Assess only the latest patient message for a potentially immediate emergency.
Return emergency=true for clear signs such as severe difficulty breathing,
severe chest pain, loss of consciousness, sudden severe weakness or trouble
speaking, seizure, severe uncontrolled bleeding, suicidal intent, or a severe
allergic reaction with breathing difficulty. Do not infer an emergency from
unrelated or ambiguous statements. Never give a diagnosis.

Patient statement:
{answer}
"""


def calculate_age(year_of_birth: Optional[int]) -> Optional[int]:
    if not year_of_birth:
        return None
    return max(0, date.today().year - year_of_birth)


def _message_from_history(message: dict[str, str]):
    if message.get("role") == "assistant":
        return AIMessage(content=message.get("content", ""))
    return HumanMessage(content=message.get("content", ""))


class LangChainSymptomAgent:
    def __init__(self, model=None):
        self.llm = model or ai_Model
        self.turn_chain = self.llm.with_structured_output(InterviewTurn)
        self.emergency_chain = self.llm.with_structured_output(EmergencyScreen)

    def _interview_turn(self, state: InterviewState) -> InterviewTurn:
        conversation = state.get("conversation", [])
        latest_answer = conversation[-1]["content"]
        history = [
            _message_from_history(message)
            for message in conversation[:-1]
        ]
        instructions = (
            f"{INTERVIEW_INSTRUCTIONS}\n\n"
            f"Verified profile context (not symptom evidence): "
            f"{state.get('patient', {})}\n"
            f"Patient answers so far: {state.get('user_turns', 0)}."
        )
        return self.turn_chain.invoke(
            [
                SystemMessage(content=instructions),
                *history,
                HumanMessage(content=latest_answer),
            ]
        )

    def _screen_emergency(self, answer: str) -> EmergencyScreen:
        return self.emergency_chain.invoke(
            EMERGENCY_INSTRUCTIONS.format(answer=answer)
        )

    def _build_report(
        self,
        state: InterviewState,
        turn: InterviewTurn,
    ) -> PatientSymptomReport:
        report = turn.report
        if report is None:
            conversation = "\n".join(
                f"{message['role']}: {message['content']}"
                for message in state.get("conversation", [])
            )
            report = self.llm.with_structured_output(
                PatientSymptomReport
            ).invoke(
                f"""
Create a concise doctor-ready symptom-history report from this interview.
Do not diagnose, recommend treatment, infer absent symptoms, or invent details.
Represent unavailable data as null or an empty list. Preserve the patient's
reported meaning and include all reported concerns.

Verified profile: {state.get('patient', {})}

Conversation:
{conversation}
"""
            )

        patient = state.get("patient", {})
        report.patient = PatientInformation(
            name=patient.get("name") or "Not provided",
            gender=patient.get("gender"),
            age=patient.get("age"),
            medical_condition=patient.get("medical_condition"),
            allergy=patient.get("allergy"),
        )
        if not report.chief_complaint.strip():
            raise ValueError("The generated report has no chief complaint.")
        return report

    def _process_turn(self, state: InterviewState) -> InterviewState:
        conversation = list(state.get("conversation", []))
        if not conversation:
            question = "What health concern or symptom would you like to discuss?"
            return {
                "question": question,
                "completed": False,
                "emergency": False,
                "conversation": [
                    {"role": "assistant", "content": question}
                ],
            }

        latest = conversation[-1]
        if latest.get("role") != "user":
            raise ValueError("The interview is waiting for a patient answer.")

        answer = latest.get("content", "").strip()
        if not answer:
            raise ValueError("Answer cannot be empty.")

        answer_state = dict(state)
        answer_state["conversation"] = conversation
        answer_state["user_turns"] = state.get("user_turns", 0) + 1

        with ThreadPoolExecutor(max_workers=2) as executor:
            turn_future = executor.submit(self._interview_turn, answer_state)
            safety_future = executor.submit(self._screen_emergency, answer)
            turn = turn_future.result()
            safety = safety_future.result()

        if safety.emergency:
            emergency_message = (
                "Your symptoms may require urgent medical attention. "
                "Please seek immediate medical care or contact your local "
                "emergency service. This interview cannot assess emergencies."
            )
            conversation.append({
                "role": "assistant",
                "content": emergency_message,
            })
            return {
                "conversation": conversation,
                "user_turns": answer_state["user_turns"],
                "question": None,
                "completed": True,
                "emergency": True,
                "emergency_message": emergency_message,
                "report": None,
            }

        if answer_state["user_turns"] >= 5:
            turn.completed = True

        if turn.completed:
            report = self._build_report(answer_state, turn)
            return {
                "conversation": conversation,
                "user_turns": answer_state["user_turns"],
                "question": None,
                "completed": True,
                "emergency": False,
                "emergency_message": None,
                "report": report.model_dump(),
            }

        question = (turn.question or "").strip()
        if not question:
            raise ValueError(
                "The interview agent returned neither a question nor a report."
            )
        conversation.append({"role": "assistant", "content": question})
        return {
            "conversation": conversation,
            "user_turns": answer_state["user_turns"],
            "question": question,
            "completed": False,
            "emergency": False,
            "emergency_message": None,
            "report": None,
        }


agent = LangChainSymptomAgent()
builder = StateGraph(InterviewState)
builder.add_node("process_turn", agent._process_turn)
builder.set_entry_point("process_turn")
builder.add_edge("process_turn", END)
interview_graph = builder.compile()


def _response(session_id: str, state: dict) -> dict:
    return PatientSummaryResponse(
        session_id=session_id,
        question=state.get("question"),
        completed=state.get("completed", False),
        emergency=state.get("emergency", False),
        emergency_message=state.get("emergency_message"),
        report=state.get("report"),
    ).model_dump()


def start_interview(db, patient):
    session_id = str(uuid.uuid4())
    patient_context = {
        "name": patient.name or "",
        "gender": patient.gender,
        "age": calculate_age(patient.year_of_birth),
        "medical_condition": patient.medical_condition,
        "allergy": patient.allergy,
    }
    initial_state: InterviewState = {
        "patient_id": str(patient.id),
        "patient": patient_context,
        "conversation": [],
        "user_turns": 0,
        "completed": False,
        "emergency": False,
    }
    result = interview_graph.invoke(initial_state)
    db_session = PatientSummarySession(
        session_id=uuid.UUID(session_id),
        patient_id=patient.id,
        session_state=result,
    )
    try:
        db.add(db_session)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _response(session_id, result)


def get_interview_session(db, patient, session_id: str):
    db_session = (
        db.query(PatientSummarySession)
        .filter(
            PatientSummarySession.session_id == uuid.UUID(session_id),
        )
        .first()
    )
    if db_session is None:
        raise PatientSummarySessionNotFound(
            "Patient summary session not found. Please start a new interview."
        )

    if db_session.patient_id != patient.id:
        raise PermissionError(
            "You are not authorized to access this session."
        )
    state = deepcopy(db_session.session_state)
    return _response(session_id, state)


def list_completed_reports(db, patient):
    sessions = (
        db.query(PatientSummarySession)
        .filter(PatientSummarySession.patient_id == patient.id)
        .order_by(PatientSummarySession.updated_at.desc())
        .all()
    )
    reports = []
    for session in sessions:
        state = session.session_state or {}
        report = state.get("report")
        if not state.get("completed") or state.get("emergency") or not report:
            continue

        reports.append({
            "session_id": str(session.session_id),
            "completed_at": session.updated_at,
            "report": report,
        })
    return reports


def get_completed_report(db, patient, session_id: str):
    db_session = (
        db.query(PatientSummarySession)
        .filter(
            PatientSummarySession.session_id == uuid.UUID(session_id),
            PatientSummarySession.patient_id == patient.id,
        )
        .first()
    )
    if db_session is None:
        raise PatientSummarySessionNotFound(
            "Symptom summary report not found."
        )

    state = db_session.session_state or {}
    report = state.get("report")
    if not state.get("completed") or state.get("emergency") or not report:
        raise PatientSummarySessionNotFound(
            "A completed symptom summary report was not found."
        )
    return report, db_session.updated_at


def process_answer(db, patient, session_id: str, answer: str):
    db_session = (
        db.query(PatientSummarySession)
        .filter(
            PatientSummarySession.session_id == uuid.UUID(session_id),
        )
        .first()
    )
    if db_session is None:
        raise PatientSummarySessionNotFound(
            "Patient summary session not found. Please start a new interview."
        )

    if db_session.patient_id != patient.id:
        raise PermissionError(
            "You are not authorized to access this session."
        )
    state = deepcopy(db_session.session_state)
    if state.get("completed"):
        return _response(session_id, state)
    if not answer or not answer.strip():
        raise ValueError("Answer cannot be empty.")

    conversation = list(state.get("conversation", []))
    conversation.append({"role": "user", "content": answer.strip()})
    state["conversation"] = conversation
    result = interview_graph.invoke(state)
    db_session.session_state = result
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _response(session_id, result)
