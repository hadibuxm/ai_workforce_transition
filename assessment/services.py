"""Business logic for parsing resumes and generating transition insights via OpenAI."""
from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass
from typing import Dict, List

from django.conf import settings
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


class UnsupportedFileType(ValueError):
    """Raised when a resume upload has an unsupported format."""


class AnalysisError(RuntimeError):
    """Raised when the OpenAI service cannot complete the analysis."""


def extract_text_from_file(uploaded_file) -> str:
    """Read an uploaded resume file and extract raw text."""
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # Reset so Django can re-read if required later.

    stream = io.BytesIO(file_bytes)

    if filename.endswith(".pdf"):
        reader = PdfReader(stream)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    if filename.endswith(".docx"):
        document = Document(stream)
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraphs).strip()

    raise UnsupportedFileType(f"Unsupported file type for {filename!r}.")


@dataclass
class AssessmentResult:
    readiness_score: int
    time_horizon: str
    risk_score: int
    recommendation: str
    reassessment_time: str
    automatable_signals: Dict[str, int]
    risk_signals: Dict[str, int]
    duty_sample: List[str]


_client = OpenAI(api_key=settings.OPENAI_API_KEY)

_SYSTEM_PROMPT = (
    "You are an AI workforce strategist. Review the provided resume or job description "
    "and determine how ready the role is for full AI automation. Provide thoughtful scores "
    "between 0 and 100 along with short supportive evidence. Respond as valid JSON only."
)


def analyze_resume(resume_text: str) -> AssessmentResult:
    """Send the extracted resume text to OpenAI and build the structured result."""
    normalized_text = resume_text.strip()
    if not normalized_text:
        raise AnalysisError("Unable to extract meaningful text from the resume.")

    payload = _request_openai_analysis(normalized_text[:12000])
    return _parse_payload(payload)


def _request_openai_analysis(text: str) -> Dict[str, object]:
    """Call the OpenAI model and return the parsed JSON payload."""
    try:
        response = _client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Resume content:\n"
                        f"{text}\n\n"
                        "Return JSON with keys: readiness_score (0-100 integer), "
                        "time_horizon (string), risk_score (0-100 integer), "
                        "recommendation (string), reassessment_time (string), "
                    ),
                },
            ],
        )
        message_content = response.choices[0].message.content
        print(f"ai response: {message_content}")
        if not message_content:
            raise AnalysisError("Empty response from OpenAI.")
        return json.loads(message_content)
    except json.JSONDecodeError as exc:
        logger.exception("OpenAI returned non-JSON response.")
        raise AnalysisError("OpenAI returned an unexpected format.") from exc
    except Exception as exc:
        logger.exception("OpenAI analysis request failed.")
        raise AnalysisError("OpenAI analysis failed. Please try again later.") from exc


def _parse_payload(payload: Dict[str, object]) -> AssessmentResult:
    """Convert the OpenAI JSON payload into an AssessmentResult."""
    readiness = _safe_int(payload.get("readiness_score"), default=0)
    risk = _safe_int(payload.get("risk_score"), default=50)

    automatable = _safe_dict(payload.get("automatable_signals"))
    risk_signals = _safe_dict(payload.get("risk_signals"))
    duty_sample = _safe_list(payload.get("duty_sample"))

    return AssessmentResult(
        readiness_score=_clamp_score(readiness),
        time_horizon=str(payload.get("time_horizon") or "Time horizon unavailable"),
        risk_score=_clamp_score(risk),
        recommendation=str(
            payload.get("recommendation")
            or "Recommendation unavailable. Rerun the assessment."
        ),
        reassessment_time=str(
            payload.get("reassessment_time")
            or "Reassessment guidance unavailable."
        ),
        automatable_signals=automatable,
        risk_signals=risk_signals,
        duty_sample=duty_sample or ["Resume duties summary unavailable."],
    )


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(value) -> Dict[str, int]:
    if isinstance(value, dict):
        return {str(k): _safe_int(v, 0) for k, v in value.items()}
    return {}


def _safe_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, int, float))]
    return []


def _clamp_score(score: int) -> int:
    return max(0, min(int(score), 100))
