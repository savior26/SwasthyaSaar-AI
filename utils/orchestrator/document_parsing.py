import os
import io
import json
import pymupdf  
import docx
from PIL import Image
import easyocr
import numpy as np
from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field
import base64
# LangChain Google GenAI Integration
from langchain_core.messages import HumanMessage, SystemMessage
from schemas.doc_schema import LabReportData, PrescriptionData
from services.prompts.data_parsing_prompt import LAB_REPORT_VISION_PROMPT, LAB_REPORT_TEXT_PROMPT ,PRESCRIPTION_VISION_PROMPT, PRESCRIPTION_TEXT_PROMPT 
from services.ai_model import ai_Model
# Type alias for combined document outputs
ParsedMedicalDocument = Union[PrescriptionData, LabReportData]


# ============================================================================
# 2. DOCUMENT CLASSIFIER & INGESTION PIPELINE
# ============================================================================

class DocumentParsingPipeline:
    def __init__(self):
        """
        Initialize:
        - EasyOCR reader for printed image fallback
        - LangChain Gemini 3.5 Flash-Lite client
        """

        self.ocr_reader = easyocr.Reader(['en'], gpu=False)

        # Model instance for LangChain Gemini integration
        self.llm = ai_Model

    # ------------------------------------------------------------------------
    # HELPERS: MULTI-PAGE FILE CONVERSION & OCR
    # ------------------------------------------------------------------------

    def _convert_file_to_images(self, file_path: str) -> List[Image.Image]:
        """Converts image files or ALL pages of a PDF/multi-page file to PIL RGB Images."""
        ext = os.path.splitext(file_path)[1].lower()
        images = []

        if ext in ['.jpg', '.jpeg', '.png']:
            img = Image.open(file_path).convert("RGB")
            # Support multi-frame images (e.g., multi-page TIFF/PNG)
            n_frames = getattr(img, 'n_frames', 1)
            for frame in range(n_frames):
                img.seek(frame)
                images.append(img.copy().convert("RGB"))
            return images

        elif ext == '.pdf':
            doc = pymupdf.open(file_path)
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            return images

        else:
            raise ValueError(f"Direct image conversion is not supported for extension '{ext}'")

    def detect_printed_handwritten(
        self,
        images: List[Image.Image]
    ):
        """
        Runs EasyOCR only ONCE for the supplied images.

        Returns:
            is_handwritten: bool
            extracted_text: str

        The same OCR result is used for:
            1. Printed/handwritten detection
            2. Printed text extraction
        """

        all_text = []
        page_is_handwritten = []

        for page_number, image in enumerate(images, start=1):

            image_np = np.array(image)

            # ============================================================
            # ONE AND ONLY ONE EasyOCR CALL
            # ============================================================
            results = self.ocr_reader.readtext(
                image_np,
                detail=1
            )

            # ------------------------------------------------------------
            # No OCR result
            # ------------------------------------------------------------
            if not results:
                page_is_handwritten.append(True)
                continue

            # ============================================================
            # Use SAME OCR results for classification
            # ============================================================

            confidences = [
                float(result[2])
                for result in results
            ]

            avg_confidence = np.mean(confidences)

            high_conf_ratio = np.mean(
                np.array(confidences) >= 0.70
            )

            word_count = len(results)

            # ============================================================
            # Use SAME OCR results for text extraction
            # ============================================================

            page_text = "\n".join(
                result[1].strip()
                for result in results
                if result[1].strip()
            )

            if page_text:
                all_text.append(
                    f"--- PAGE {page_number} [EasyOCR] ---\n"
                    f"{page_text}"
                )

            # ============================================================
            # CLASSIFY PAGE
            # ============================================================

            if (
                avg_confidence >= 0.75
                and high_conf_ratio >= 0.70
                and word_count >= 10
            ):
                # Printed
                page_is_handwritten.append(False)

            elif (
                avg_confidence < 0.50
                or high_conf_ratio < 0.30
            ):
                # Handwritten
                page_is_handwritten.append(True)

            else:
                # Low-confidence OCR is routed to the vision parser rather
                # than failing before the vision fallback can inspect it.
                page_is_handwritten.append(True)

        # ================================================================
        # DOCUMENT-LEVEL RESULT
        # ================================================================

        is_handwritten = any(page_is_handwritten)

        extracted_text = "\n\n".join(all_text)

        return is_handwritten, extracted_text

    def extract_printed_text(self, file_path: str, pre_extracted_text: Optional[str] = None) -> str:
        """
        Extracts native text from digital formats (.txt, .docx, multi-page .pdf)
        or applies EasyOCR fallback across all pages for printed image documents.
        """
        # ================================================================
        # REUSE OCR RESULT
        # ================================================================

        if pre_extracted_text is not None:
            return pre_extracted_text

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    full_text.append(p.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        full_text.append(" | ".join(row_text))
            return "\n".join(full_text)

        elif ext == ".pdf":
            doc = pymupdf.open(file_path)

            processed_pages = []
            ocr_used = False

            for page_number, page in enumerate(doc, start=1):

                # ========================================================
                # 1. Try native PDF text extraction
                # ========================================================
                text = page.get_text("text").strip()

                if text:
                    processed_pages.append(
                        f"--- PAGE {page_number} [PyMuPDF] ---\n{text}"
                    )
                    continue

                # ========================================================
                # 2. No native text → render page as image
                # ========================================================
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False
                )

                # Convert PDF page → PNG bytes
                img_bytes = pix.tobytes("png")

                # ========================================================
                # 3. PNG bytes → NumPy array
                # ========================================================
                image = Image.open(
                    io.BytesIO(img_bytes)
                )

                image_np = np.array(image)

                # ========================================================
                # 4. EasyOCR
                # ========================================================
                ocr_results = self.ocr_reader.readtext(
                    image_np,
                    detail=0
                )

                ocr_text = "\n".join(
                    item.strip()
                    for item in ocr_results
                    if item.strip()
                )

                ocr_used = True

                # ========================================================
                # 5. Store OCR result
                # ========================================================
                if ocr_text:
                    processed_pages.append(
                        f"--- PAGE {page_number} [EasyOCR] ---\n"
                        f"{ocr_text}"
                    )
                else:
                    processed_pages.append(
                        f"--- PAGE {page_number} [EasyOCR] ---\n"
                        "[No text detected]"
                    )

            doc.close()
            result = "\n\n".join(processed_pages)

            if ocr_used:
                print("OCR was used for one or more pages.")
            else:
                print("OCR was not required.")

            return result

        elif ext in ['.jpg', '.jpeg', '.png']:
            images = self._convert_file_to_images(file_path)
            ocr_text_pages = []
            for img in images:
                img_np = np.array(img)
                ocr_results = self.ocr_reader.readtext(img_np, detail=0)
                ocr_text_pages.append("\n".join(ocr_results))
            return "\n--- PAGE BREAK ---\n".join(ocr_text_pages)

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    # ------------------------------------------------------------------------
    # PARSING PIPELINES (LANGCHAIN GEMINI)
    # ------------------------------------------------------------------------

    def parse_printed_text_with_langchain(
        self,
        raw_text: str,
        doc_type: Literal["PRESCRIPTION", "LAB_REPORT"]
    ) -> ParsedMedicalDocument:

        """Parses extracted printed multi-page text using LangChain Google GenAI structured output."""

        schema = PrescriptionData if doc_type == "PRESCRIPTION" else LabReportData
        prompt = PRESCRIPTION_TEXT_PROMPT if doc_type == "PRESCRIPTION" else LAB_REPORT_TEXT_PROMPT

        structured_llm = self.llm.with_structured_output(schema)

        messages = [
            SystemMessage(content="You are an expert clinical document parser."),
            HumanMessage(content=f"{prompt}\n\nRAW DOCUMENT TEXT:\n{raw_text}")
        ]

        return structured_llm.invoke(messages)

    def parse_handwritten_with_langchain_vision(
        self,
        file_path: str,
        doc_type: Literal["PRESCRIPTION", "LAB_REPORT"]
    ) -> ParsedMedicalDocument:
        """
        Parses multi-page handwritten documents directly using LangChain + Gemini 3.5 Flash-Lite Vision.
        Converts all document pages into base64 image content blocks in a single request.
        """


        schema = PrescriptionData if doc_type == "PRESCRIPTION" else LabReportData
        prompt = PRESCRIPTION_VISION_PROMPT if doc_type == "PRESCRIPTION" else LAB_REPORT_VISION_PROMPT

        images = self._convert_file_to_images(file_path)
        content_blocks: List[Union[str, Dict[str, Any]]] = [{"type": "text", "text": prompt}]

        # Prepare multimodal vision payload across all pages
        for idx, img in enumerate(images):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            content_blocks.append({
                "type": "text",
                "text": f"Page {idx + 1}:"
            })
            content_blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_data}"
                }
            })

        structured_llm = self.llm.with_structured_output(schema)
        messages = [
            SystemMessage(content="You are an expert clinical document vision parser."),
            HumanMessage(content=content_blocks)
        ]

        return structured_llm.invoke(messages)

    # ------------------------------------------------------------------------
    # MASTER ORCHESTRATOR
    # ------------------------------------------------------------------------

    def process_document(
        self,
        file_path: str,
        doc_type: Literal["PRESCRIPTION", "LAB_REPORT"]
    ) -> ParsedMedicalDocument:
        """
        Master Pipeline Execution Flow:
        1. Validates document format (.jpg, .jpeg, .png, .txt, .pdf, .docx).
        2. Routes digital text files directly to printed pipeline.
        3. Handwritten is detected by Groq
        4. Invokes EasyOCR / PyMuPDF + LangChain for printed documents.
        5. Invokes LangChain Vision (gemini-3.5-flash-lite) for handwritten documents.
        """
        ext = os.path.splitext(file_path)[1].lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.txt', '.pdf', '.docx']

        if ext not in allowed_extensions:
            raise ValueError(f"File extension '{ext}' is not allowed. Choose from {allowed_extensions}")

        # Non-visual text formats are processed as printed documents directly
        if ext in ['.txt', '.docx']:
            print(f"[{file_path}] Digital text format detected. Processing printed pipeline...")
            raw_text = self.extract_printed_text(file_path)

            return self.parse_printed_text_with_langchain(raw_text, doc_type=doc_type)

        # Convert images or PDF pages to evaluate handwriting
        page_images = self._convert_file_to_images(file_path)
        is_handwritten, raw_text = self.detect_printed_handwritten(page_images)


        if is_handwritten:
            print(f"[{file_path}] Handwriting detected by Llama model on Groq. Routing to Gemini Vision Pipeline...")
            return self.parse_handwritten_with_langchain_vision(file_path, doc_type=doc_type)
        else:
            print(f"[{file_path}] Printed document detected by Llama model on Groq. Routing to Printed Pipeline...")
            raw_text = self.extract_printed_text(file_path,pre_extracted_text=raw_text)
            return self.parse_printed_text_with_langchain(raw_text, doc_type=doc_type)



DocumentPipeline = DocumentParsingPipeline()

# if __name__ == "__main__":
#     pipeline = DocumentParsingPipeline()

#     # Example 1: Multi-page Prescription PDF or Image
#     sample_report = "printed_prescription.png"
#     if os.path.exists(sample_report):
#         prescription_result = pipeline.process_document(
#             file_path=sample_report,
#             doc_type="PRESCRIPTION"
#         )
#         print("\n--- PARSED prescription_report DATA ---")
#         print(prescription_result.model_dump_json(indent=2))