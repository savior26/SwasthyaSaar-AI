from fastapi import FastAPI
from routes import (
    auth,
    dashboard,
    document,
    lab_graph,
    medications_display,
    patient_summary,
    safety_alerts,
    user,
    auth_page
)
from database import engine
from models import model
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text




app=FastAPI()

model.Base.metadata.create_all(engine)
if "processing_stage" not in {
    column["name"]
    for column in inspect(engine).get_columns("medical_documents")
}:
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE medical_documents "
                "ADD COLUMN processing_stage VARCHAR(50)"
            )
        )

app.mount("/static",StaticFiles(directory="static"),name="static")

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(document.router)
app.include_router(medications_display.router)
app.include_router(lab_graph.router)
app.include_router(patient_summary.router)
app.include_router(safety_alerts.router)
app.include_router(dashboard.router)
app.include_router(auth_page.router)