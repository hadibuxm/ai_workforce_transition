"""Business logic for coordinating with OpenAI for role assessments."""
from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".pdf", ".docx")


class UnsupportedFileType(ValueError):
    """Raised when a role document upload has an unsupported format."""


class AnalysisError(RuntimeError):
    """Raised when the OpenAI service cannot complete the analysis."""


@dataclass
class AssessmentResult:
    readiness_score: int
    readiness_category: str
    time_horizon: str
    risk_score: int
    recommendation: str
    reassessment_time: str
    automatable_signals: Dict[str, int]
    risk_signals: Dict[str, int]
    duty_sample: List[str]
    role_excerpt: str
    research_guidance: str
    research_insights: List[str]


_client = OpenAI(api_key=settings.OPENAI_API_KEY)

_SYSTEM_PROMPT = (
    "You are an AI workforce strategist. Use the provided role profile or role description to evaluate how ready the "
    "role is for unsupervised AI automation. When needed, leverage the available web search tool to ground your "
    "guidance in current automation benchmarks and industry trends. Respond in valid JSON only. like ```json { ... } "
    "````"
)


def analyze_role(*, uploaded_file=None, role_description: str | None = None) -> AssessmentResult:
    """Upload the role document or submit a role description to OpenAI, trigger an analysis, and return structured results."""
    if bool(uploaded_file) == bool(role_description):
        raise ValueError("Provide exactly one input source for analysis.")

    if uploaded_file:
        _validate_extension(uploaded_file.name)
        file_resource = _upload_role_document_to_openai(uploaded_file)
        try:
            payload = _request_openai_analysis(file_id=file_resource.id)
        finally:
            _delete_remote_file(file_resource.id)
    else:
        payload = _request_openai_analysis(role_description=role_description or "")
    return _parse_payload(payload)


def _validate_extension(filename: str) -> None:
    lowered = (filename or "").lower()
    if not any(lowered.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        raise UnsupportedFileType("Unsupported file type. Please upload a PDF or DOCX file.")


def _upload_role_document_to_openai(uploaded_file):
    """Upload the raw role document to OpenAI's file store."""
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    try:
        buffer = io.BytesIO(file_bytes)
        buffer.name = uploaded_file.name
        return _client.files.create(file=buffer, purpose="assistants")
    except Exception as exc:
        logger.exception("Failed to upload role document to OpenAI.", exc_info=exc)
        raise AnalysisError("Failed to upload role document for analysis. Please try again.") from exc


def extract_and_load_json(text):
    # Regex pattern to match JSON structure
    json_pattern = r'```json\n(\{.*?\})\n```'
    
    # Search for JSON in the provided text
    json_match = re.search(json_pattern, text, re.DOTALL)
    
    if json_match:
        try:
            # Load the matched JSON string into a Python dictionary
            json_data = json.loads(json_match.group(1))  # Corrected to group(1)
            return json_data
        except json.JSONDecodeError:
            print("Error decoding JSON.")
            return None
    else:
        print("No JSON found.")
        return None
    
def _request_openai_analysis(*, file_id: str | None = None, role_description: str | None = None) -> Dict[str, object]:
    """Call the OpenAI Responses API and return the parsed JSON payload."""
    if bool(file_id) == bool(role_description):
        raise ValueError("Expected exactly one of file_id or role_description.")

    if role_description is not None:
        role_description = role_description.strip()

    instructions = (
        "Review the provided material to estimate automation readiness. If you need external references, use the web "
        "search tool. Return JSON with keys: readiness_score (0-100 integer), "
        "time_horizon (string), risk_score (0-100 integer), recommendation (string), "
        "reassessment_time (string), automatable_signals (object label->integer), "
        "risk_signals (object label->integer), duty_sample (array of up to 8 concise bullets), "
        "role_excerpt (string under 600 characters highlighting notable duties), "
        "research_insights (array of short facts sourced via search when applicable)."
    )

    try:
        response = _client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": _SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": instructions},
                        (
                            {"type": "input_file", "file_id": file_id}
                            if file_id
                            else {
                                "type": "input_text",
                                "text": f"Role description:\n{role_description}",
                            }
                        ),
                    ],
                },
            ],
            tools=[{"type": "web_search"}],
            tool_choice="auto",
        )
        message_text = _extract_output_text(response)
        print(f"OpenAI response text: {message_text}")
        # return json.loads(message_text)
        return extract_and_load_json(message_text)
    except json.JSONDecodeError as exc:
        logger.exception("OpenAI returned non-JSON response.")
        raise AnalysisError("OpenAI returned an unexpected format.") from exc
    except Exception as exc:
        logger.exception("OpenAI analysis request failed.")
        raise AnalysisError("OpenAI analysis failed. Please try again later.") from exc


def _extract_output_text(response) -> str:
    """Normalize the Responses API output into a text string."""
    if getattr(response, "output", None):
        chunks: List[str] = []
        for item in response.output:
            for content in getattr(item, "content", []):
                if getattr(content, "type", "") == "output_text":
                    chunks.append(getattr(content, "text", ""))
        if chunks:
            return "".join(chunks).strip()

    if getattr(response, "output_text", None):
        return response.output_text.strip()

    raise AnalysisError("OpenAI returned an empty response.")


def _delete_remote_file(file_id: str) -> None:
    """Best-effort cleanup for uploaded files to avoid unnecessary storage."""
    try:
        _client.files.delete(file_id)
    except Exception:
        logger.warning("Unable to delete OpenAI file %s after analysis.", file_id)


def _parse_payload(payload: Dict[str, object]) -> AssessmentResult:
    """Convert the OpenAI JSON payload into an AssessmentResult."""
    readiness = _safe_int(payload.get("readiness_score"), default=0)
    risk = _safe_int(payload.get("risk_score"), default=50)

    transformed_readiness = _transpose_readiness_score(readiness)
    readiness_category = _readiness_category(transformed_readiness)
    research_guidance = _research_guidance(transformed_readiness)

    automatable = _safe_dict(payload.get("automatable_signals"))
    risk_signals = _safe_dict(payload.get("risk_signals"))
    duty_sample = _safe_list(payload.get("duty_sample"))
    research = _safe_list(payload.get("research_insights"))

    return AssessmentResult(
        readiness_score=transformed_readiness,
        readiness_category=readiness_category,
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
        duty_sample=duty_sample or ["Role duties summary unavailable."],
        role_excerpt=str(payload.get("role_excerpt") or "Role excerpt unavailable."),
        research_guidance=research_guidance,
        research_insights=research,
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
        sanitized: List[str] = []
        for item in value:
            if isinstance(item, str):
                sanitized.append(item)
            elif isinstance(item, (int, float)):
                sanitized.append(str(item))
        return sanitized
    return []


def _clamp_score(score: int) -> int:
    return max(0, min(int(score), 100))


def _transpose_readiness_score(score: int) -> int:
    """Normalize the model readiness score onto a 0-100 scale with 75% as the maximum readiness anchor."""
    clamped = _clamp_score(score)
    if clamped <= 0:
        return 0
    adjusted = ((clamped - 1) * 74.0 / 99.0) + 1
    scaled = (adjusted / 75.0) * 100.0
    return _clamp_score(round(scaled))


def _readiness_category(score: int) -> str:
    if score >= 75:
        return "Ready for full transition"
    if score > 50:
        return "AI-assisted partial transition (FTE reduction, but not a full replacement)"
    return "Productivity improvement with AI, but revisit transition at the suggested timeframe"


def _research_guidance(score: int) -> str:
    if score > 74:
        return (
            "This role might be ready for full transition as most of its requirements can be replicated by AI if "
            "the functions are properly designed and mapped and all the risks are carefully considered and mitigated."
        )
    if score > 50:
        return (
            "Focus research on orchestrating AI-assisted partial transitions, emphasizing hybrid workflows, "
            "targeted FTE reductions, and pinpointing the safeguards human oversight must provide."
        )
    return (
        "Direct research toward productivity boosters and risk mitigation. Document lessons learned and revisit "
        "the transition strategy at the recommended reassessment horizon to gauge readiness improvements."
    )
