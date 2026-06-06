"""
Client for BytePlus ModelArk Seed-2.0-mini-260428 via OpenAI-compatible SDK.
Handles multimodal analysis (ASR, OCR, visual understanding) per video segment.
"""
from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from config import ARK_API_KEY, ARK_BASE_URL, MODEL_ID

_client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)

# Disable the model's deep-thinking mode for these structured extraction tasks.
# Seed is a reasoning model; with thinking on + a small token budget it can spend
# the whole budget "thinking" and return empty content, yielding blank segments.
_THINKING_OFF = {"thinking": {"type": "disabled"}}


def _extract_message_text(response) -> str:
    """Return the assistant text, falling back to reasoning_content if needed."""
    msg = response.choices[0].message
    text = (msg.content or "").strip()
    if not text:
        text = (getattr(msg, "reasoning_content", None) or "").strip()
    return text


def _extract_json(raw: str) -> dict | None:
    """Robustly pull the first JSON object out of a model response."""
    if not raw:
        return None
    # Strip code fences if present
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else raw
    # Otherwise grab the outermost {...}
    if not fenced:
        brace = re.search(r"\{.*\}", candidate, re.DOTALL)
        if brace:
            candidate = brace.group(0)
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None


def _usage_tokens(usage) -> dict:
    prompt_details = getattr(usage, "prompt_tokens_details", None) or {}
    cache_read = (
        prompt_details.get("cached_tokens", 0)
        if isinstance(prompt_details, dict)
        else getattr(prompt_details, "cached_tokens", 0)
    )
    return {
        "input": getattr(usage, "prompt_tokens", 0),
        "output": getattr(usage, "completion_tokens", 0),
        "cache_read": cache_read or 0,
    }

_ANALYSIS_PROMPT = """
You are a multimodal video analysis expert for Southeast Asian e-commerce livestreams.

Analyze the provided video frames (1 frame/second) for this segment and return ONLY a valid JSON object with these fields:
{
  "transcript": "<spoken words / ASR transcript in original language>",
  "ocr_text": "<all visible text on screen: prices, discount codes, vouchers, brand names>",
  "audio_event": "<describe notable sounds: jingle, applause, countdown, silence>",
  "detected_skus": "<comma-separated product SKUs or product names visible/mentioned>",
  "energy_score": <float 0.0-1.0 representing audience engagement level>
}

Rules:
- transcript: capture exact spoken language (Vietnamese, English, Thai, mixed code-switching)
- ocr_text: extract ALL visible text including prices (₫, $, ฿), promo codes, countdowns
- detected_skus: list product IDs or names, empty string if none
- energy_score: 0=boring/quiet, 1=peak excitement (flash sale countdown, crowd cheering)
- Return ONLY the JSON object, no markdown, no explanation
"""

_QUERY_PROMPT = """
You are a precise video Q&A assistant for e-commerce video analysis.

Given the video segment metadata below and the user's question, provide a grounded answer.

Segment data:
{segment_data}

User question: {question}
Language: {language}

Return ONLY a valid JSON object:
{{
  "answer": "<direct answer in the requested language>",
  "timestamp": <most relevant second in the segment, float>,
  "reasoning_proof": "<1-2 sentences explaining what evidence in the video supports this answer>"
}}
"""

_COMPLIANCE_PROMPT = """
You are a compliance auditor for e-commerce livestream content.

Given this segment's spoken transcript and on-screen text, identify any factual inconsistencies or misleading claims.

Transcript (spoken): {transcript}
On-screen text (OCR): {ocr_text}

Return ONLY a valid JSON object:
{{
  "has_issue": <true|false>,
  "issue_description": "<description of the inconsistency, empty string if none>",
  "severity": "<high|medium|low|none>"
}}
"""


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _image_content(path: Path) -> dict:
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{_encode_image(path)}",
            "detail": "low",
        },
    }


def _video_content(path: Path) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {
        "type": "video_url",
        "video_url": {"url": f"data:video/mp4;base64,{b64}"},
    }


_VIDEO_ANALYSIS_PROMPT = """
You are a multimodal video analysis expert for Southeast Asian e-commerce livestreams.

Watch and LISTEN to this short video segment, then return ONLY a valid JSON object:
{
  "transcript": "<verbatim spoken words (ASR) in the original spoken language>",
  "ocr_text": "<all visible on-screen text: prices, discount codes, vouchers, brand names>",
  "audio_event": "<notable sounds: speech, music/jingle, applause, countdown, silence>",
  "detected_skus": "<comma-separated product names/SKUs shown or mentioned>",
  "energy_score": <float 0.0-1.0 for audience engagement / excitement>
}

Rules:
- transcript: transcribe the ACTUAL SPEECH you hear (Vietnamese, English, Thai, or mixed code-switching). Do NOT leave empty if anyone is talking.
- ocr_text: extract ALL visible text including prices (đ, $, ฿), promo codes, countdowns
- detected_skus: product IDs or names, empty string if none
- energy_score: 0=quiet/boring, 1=peak excitement
- Return ONLY the JSON object, no markdown, no explanation
"""


def analyze_segment_video(
    clip_path: Path,
    start_sec: float,
    end_sec: float,
) -> dict[str, Any]:
    """
    Send a compressed video clip (with audio) to Seed for full multimodal
    analysis including ASR. Returns parsed JSON with the standard fields.
    """
    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VIDEO_ANALYSIS_PROMPT},
                    _video_content(clip_path),
                ],
            }
        ],
        max_tokens=1500,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw)
    result = parsed if parsed is not None else {
        "transcript": "",
        "ocr_text": "",
        "audio_event": "",
        "detected_skus": "",
        "energy_score": 0.0,
    }

    result["_latency_ms"] = latency_ms
    result["_tokens"] = _usage_tokens(response.usage)
    return result


def analyze_segment(
    frame_paths: list[Path],
    start_sec: float,
    end_sec: float,
    max_frames: int = 8,
) -> dict[str, Any]:
    """
    Send sampled frames from a segment to Seed-2.0-mini for multimodal analysis.
    Returns parsed JSON with transcript, ocr_text, audio_event, detected_skus, energy_score.
    """
    if not frame_paths:
        return {
            "transcript": "",
            "ocr_text": "",
            "audio_event": "",
            "detected_skus": "",
            "energy_score": 0.0,
        }

    # Sample evenly if too many frames
    if len(frame_paths) > max_frames:
        step = len(frame_paths) / max_frames
        frame_paths = [frame_paths[int(i * step)] for i in range(max_frames)]

    content: list[dict] = [{"type": "text", "text": _ANALYSIS_PROMPT}]
    for p in frame_paths:
        if p.exists():
            content.append(_image_content(p))

    # Structure as system + user to enable prompt caching on the system prompt
    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": _ANALYSIS_PROMPT},
            {"role": "user", "content": [c for c in content if c["type"] != "text"]},
        ],
        max_tokens=1500,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw)
    result = parsed if parsed is not None else {
        "transcript": "",
        "ocr_text": "",
        "audio_event": "",
        "detected_skus": "",
        "energy_score": 0.0,
    }

    result["_latency_ms"] = latency_ms
    result["_tokens"] = _usage_tokens(response.usage)
    return result


def answer_question(
    segment_data: list[dict],
    question: str,
    language: str = "vi",
    frame_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Stage 2: send candidate segments + question to Seed for deep reasoning."""
    segment_text = json.dumps(segment_data, ensure_ascii=False, indent=2)
    prompt = _QUERY_PROMPT.format(
        segment_data=segment_text,
        question=question,
        language=language,
    )

    user_content: list[dict] = [{"type": "text", "text": prompt}]
    if frame_paths:
        for p in (frame_paths or [])[:4]:
            if p.exists():
                user_content.append(_image_content(p))

    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=1500,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw)
    if parsed is not None:
        result = parsed
    else:
        # No JSON — use the raw text as the answer so the user still sees something
        result = {
            "answer": raw or "Sorry, I couldn't generate an answer for this question.",
            "timestamp": None,
            "reasoning_proof": "",
        }

    result["_latency_ms"] = latency_ms
    result["_tokens"] = _usage_tokens(response.usage)
    return result


def check_compliance(transcript: str, ocr_text: str) -> dict[str, Any]:
    """Check for spoken-vs-visual inconsistencies in a segment."""
    prompt = _COMPLIANCE_PROMPT.format(transcript=transcript, ocr_text=ocr_text)

    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw)
    result = parsed if parsed is not None else {
        "has_issue": False,
        "issue_description": "",
        "severity": "none",
    }

    result["_latency_ms"] = latency_ms
    return result
