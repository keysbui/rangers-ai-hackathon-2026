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

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
    return _client

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

_SUMMARY_PROMPT = """
You are an e-commerce livestream analyst.

The data below comes from a processed video. It contains scene timestamps,
seller speech transcripts, on-screen OCR, and detected product/SKU names.

Video timeline data:
{timeline_data}

Create a concise video summary in all supported UI languages: Vietnamese (vi),
English (en), and Thai (th).

For each language return:
- overview: one short paragraph explaining what the video is about.
- product_details: one paragraph or compact bullet-style text listing products,
  colors, prices, sizes, promotions, variants, and any other concrete product
  details found in transcript/OCR/SKU fields.

Rules:
- Focus on the seller's dialogue and concrete on-screen product evidence.
- If a color, price, size, or variant is not found, do not invent it.
- Keep each field practical and readable for a shopper or operator.
- Return ONLY a valid JSON object in this exact shape:
{{
  "vi": {{
    "overview": "<Vietnamese overview>",
    "product_details": "<Vietnamese product details>"
  }},
  "en": {{
    "overview": "<English overview>",
    "product_details": "<English product details>"
  }},
  "th": {{
    "overview": "<Thai overview>",
    "product_details": "<Thai product details>"
  }}
}}
"""

_POLICY_AUDIT_PROMPT = """
You are a TikTok Shop livestream replay content policy auditor.

Analyze the segment data below and identify any potential violations of TikTok Shop content policies.
Only flag items that are supported by clear evidence in transcript or on-screen text.

Segment transcript (spoken): {transcript}
Segment on-screen text (OCR): {ocr_text}
Detected SKUs / products: {detected_skus}

Return ONLY a valid JSON object:
{{
  "violations": [
    {{
      "rule_id": "<stable_id>",
      "rule_name": "<short name in Vietnamese>",
      "policy_category": "<category>",
      "severity": "<low|medium|high>",
      "confidence": <float 0.0-1.0>,
      "evidence": {{
        "transcript_snippet": "<short quote or empty>",
        "ocr_snippet": "<short quote or empty>",
        "why": "<1-2 sentences>"
      }}
    }}
  ]
}}

Rule ids/categories to use when relevant:
- OFF_PLATFORM_REDIRECT: chuyển hướng người dùng ra ngoài nền tảng (link, QR, số điện thoại, email, MXH, nhắn tin)
- PROHIBITED_PRODUCTS: quảng bá sản phẩm bị cấm/không được hỗ trợ (thuốc kê đơn, vũ khí, thuốc lá/ma túy)
- RESTRICTED_PRODUCTS: quảng bá sản phẩm bị hạn chế khi chưa đủ điều kiện
- GAMBLING: nội dung cờ bạc/cá cược/lô đề
- SEXUAL_CONTENT: nội dung khiêu dâm hoặc gợi dục
- MINORS_TARGETING: nhắm mục tiêu trẻ vị thành niên
- SHOCKING_CONTENT: nội dung giật gân/gây sốc/bạo lực
- POLITICAL_CONTENT: nội dung chính trị
- SENSITIVE_EVENTS: lợi dụng sự kiện nhạy cảm
- MISLEADING_CLAIMS: nội dung sai lệch/gây hiểu lầm/phóng đại
- BAIT_AND_SWITCH: bait-and-switch (giá/ưu đãi/đổi sản phẩm)
- FAKE_ENGAGEMENT: tương tác giả/spam/buff
- IRRELEVANT_PROMOTION: quảng cáo không liên quan, không quảng bá rõ sản phẩm đang bán
- NON_INTERACTIVE_CONTENT: nội dung không tương tác (gần như không nói/không có hoạt động ý nghĩa)

If there is no violation, return {{"violations": []}}.
Return ONLY JSON, no markdown, no explanation.
"""

_RE_URL = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_RE_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_RE_PHONE_VN = re.compile(r"(?<!\d)(0\d{8,10})(?!\d)")
_RE_OFF_PLATFORM_WORDS = re.compile(
    r"\b(zalo|telegram|whatsapp|facebook|fb|inbox|nhắn tin|nhan tin|sđt|sdt|"
    r"số điện thoại|so dien thoai|liên hệ|lien he|call|hotline|dm|messenger|"
    r"link bio|bio|quét qr|quet qr|qr code|qr)\b",
    re.IGNORECASE,
)
_RE_GAMBLING = re.compile(r"\b(lô đề|lo de|cá độ|ca do|casino|bet|cược|cuoc)\b", re.IGNORECASE)
_RE_PROHIBITED = re.compile(
    r"\b(ma túy|ma tuy|cần sa|can sa|heroin|cocaine|thuốc lá|thuoc la|vape|pod|"
    r"súng|sung|đạn|dan|vũ khí|vu khi|bom|lựu đạn|luu dan)\b",
    re.IGNORECASE,
)
_RE_WEIGHT_CLAIM = re.compile(
    r"\b(giảm cân|giam can|đốt mỡ|dot mo|tan mỡ|"
    r"giảm\s*\d+\s*kg|giam\s*\d+\s*kg|tăng cân|tang can)\b",
    re.IGNORECASE,
)


def _policy_audit_local(transcript: str, ocr_text: str, detected_skus: str) -> list[dict[str, Any]]:
    text = "\n".join([transcript or "", ocr_text or "", detected_skus or ""]).strip()
    if not text:
        return []

    violations: list[dict[str, Any]] = []

    if _RE_URL.search(text) or _RE_EMAIL.search(text) or _RE_PHONE_VN.search(text) or _RE_OFF_PLATFORM_WORDS.search(text):
        violations.append(
            {
                "rule_id": "OFF_PLATFORM_REDIRECT",
                "rule_name": "Chuyển hướng ra ngoài nền tảng",
                "policy_category": "OFF_PLATFORM_REDIRECT",
                "severity": "high",
                "confidence": 0.9,
                "evidence": {
                    "transcript_snippet": transcript or "",
                    "ocr_snippet": ocr_text or "",
                    "why": "Phát hiện dấu hiệu điều hướng người mua ra ngoài nền tảng (link/QR/số điện thoại/email/MXH).",
                },
            }
        )

    if _RE_GAMBLING.search(text):
        violations.append(
            {
                "rule_id": "GAMBLING",
                "rule_name": "Nội dung cờ bạc/cá cược",
                "policy_category": "GAMBLING",
                "severity": "high",
                "confidence": 0.85,
                "evidence": {
                    "transcript_snippet": transcript or "",
                    "ocr_snippet": ocr_text or "",
                    "why": "Phát hiện từ khóa liên quan cờ bạc/cá cược.",
                },
            }
        )

    if _RE_PROHIBITED.search(text):
        violations.append(
            {
                "rule_id": "PROHIBITED_PRODUCTS",
                "rule_name": "Sản phẩm bị cấm/không hỗ trợ",
                "policy_category": "PROHIBITED_PRODUCTS",
                "severity": "high",
                "confidence": 0.8,
                "evidence": {
                    "transcript_snippet": transcript or "",
                    "ocr_snippet": ocr_text or "",
                    "why": "Phát hiện từ khóa liên quan sản phẩm bị cấm/không hỗ trợ.",
                },
            }
        )

    if _RE_WEIGHT_CLAIM.search(text):
        violations.append(
            {
                "rule_id": "MISLEADING_CLAIMS",
                "rule_name": "Tuyên bố quản lý cân nặng",
                "policy_category": "MISLEADING_CLAIMS",
                "severity": "medium",
                "confidence": 0.75,
                "evidence": {
                    "transcript_snippet": transcript or "",
                    "ocr_snippet": ocr_text or "",
                    "why": "Phát hiện tuyên bố liên quan giảm/tăng cân có nguy cơ vi phạm.",
                },
            }
        )

    return violations


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
    response = _get_client().chat.completions.create(
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
    response = _get_client().chat.completions.create(
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
    response = _get_client().chat.completions.create(
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


_HIGHLIGHT_PROMPT = """
You are a world-class Video Editor. Your mission is to find the absolute best "viral" moments from an e-commerce livestream and define precise cut points.

Trends: {trends}

CONTEXT (Full Video Sequence):
The following JSON is a chronological list of video segments. 
CRITICAL: IGNORE the segment boundaries. Treat this as one continuous timeline from 0.0 to the end.
{segment_data}

CRITICAL EDITING RULES:
1. **NO BOUNDARIES**: Your highlight `refined_start` and `refined_end` should be based on the STORY, not the provided segment times. If a story starts at 12.4s and ends at 78.2s, use exactly those times.
2. **COMPLETE STORY ARC**: A highlight MUST be a complete "mini-video". 
   - It starts when the host begins a new pitch, a new product, or a new energetic hook.
   - It ends ONLY after the pitch is complete, the price is shown, and the host reaches a natural pause.
   - Most good highlights will be between 30 and 90 seconds. If your output is exactly 30 seconds, you are likely failing to capture the full story.
3. **DIALOGUE INTEGRITY**: 
   - Start the cut EXACTLY at the beginning of a sentence.
   - End the cut EXACTLY at the end of a sentence. 
   - NEVER cut while someone is mid-word or mid-sentence.
4. **NO CHOPPY CUTS**: If you find a high-energy moment, look 10-20 seconds before and after it to ensure the context is captured.

OUTPUT FORMAT (Return ONLY a valid JSON object):
{{
  "highlights": [
    {{
      "original_anchor": <the start time of the most energetic segment in this highlight>,
      "refined_start": <absolute_start_time_in_seconds_from_video_start>,
      "refined_end": <absolute_end_time_in_seconds_from_video_start_after_completing_the_story>,
      "reason": "Explain the full story arc of this cut and why it's not choppy",
      "ad_copy": "Viral caption in {language}",
      "viral_score": <0-100>
    }},
    ...
  ]
}}
"""


def rank_highlights(
    segment_data: list[dict],
    trends: str,
    language: str = "vi",
) -> dict[str, Any]:
    """Use Seed to select the best segments for ad highlights based on trends."""
    segment_text = json.dumps(segment_data, ensure_ascii=False, indent=2)
    prompt = _HIGHLIGHT_PROMPT.format(
        segment_data=segment_text,
        trends=trends,
        language=language,
    )

    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw)
    result = parsed if parsed is not None else {"highlights": []}

    result["_latency_ms"] = latency_ms
    result["_tokens"] = _usage_tokens(response.usage)
    return result


def summarize_video(timeline_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Create video-level summaries for all supported UI languages."""
    compact = []
    for seg in timeline_data:
        compact.append(
            {
                "timestamp_start": seg.get("timestamp_start"),
                "timestamp_end": seg.get("timestamp_end"),
                "transcript": seg.get("transcript") or "",
                "ocr_text": seg.get("ocr_text") or "",
                "detected_skus": seg.get("detected_skus") or "",
            }
        )

    prompt = _SUMMARY_PROMPT.format(
        timeline_data=json.dumps(compact, ensure_ascii=False, indent=2)
    )

    t0 = time.time()
    response = _get_client().chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw) or {}
    result: dict[str, Any] = {}
    for language in ("vi", "en", "th"):
        value = parsed.get(language) if isinstance(parsed, dict) else None
        if not isinstance(value, dict):
            value = {}
        result[language] = {
            "overview": str(value.get("overview") or "").strip(),
            "product_details": str(value.get("product_details") or "").strip(),
        }

    result["_latency_ms"] = latency_ms
    result["_tokens"] = _usage_tokens(response.usage)
    return result


def check_compliance(transcript: str, ocr_text: str) -> dict[str, Any]:
    """Check for spoken-vs-visual inconsistencies in a segment."""
    prompt = _COMPLIANCE_PROMPT.format(transcript=transcript, ocr_text=ocr_text)

    t0 = time.time()
    response = _get_client().chat.completions.create(
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


def policy_audit_segment(
    transcript: str,
    ocr_text: str,
    detected_skus: str = "",
    mode: str = "auto",
) -> dict[str, Any]:
    local = _policy_audit_local(transcript, ocr_text, detected_skus)
    if mode == "fast":
        return {"violations": local, "_model_used": False}
    if mode == "auto" and local:
        return {"violations": local, "_model_used": False}

    prompt = _POLICY_AUDIT_PROMPT.format(
        transcript=transcript or "",
        ocr_text=ocr_text or "",
        detected_skus=detected_skus or "",
    )

    t0 = time.time()
    response = _get_client().chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        extra_body=_THINKING_OFF,
    )
    latency_ms = (time.time() - t0) * 1000

    raw = _extract_message_text(response)
    parsed = _extract_json(raw) or {}
    violations = parsed.get("violations") if isinstance(parsed, dict) else None
    if not isinstance(violations, list):
        violations = []

    if local and mode in {"auto", "full"}:
        seen = {(v.get("rule_id"), v.get("policy_category")) for v in violations if isinstance(v, dict)}
        for v in local:
            key = (v.get("rule_id"), v.get("policy_category"))
            if key not in seen:
                violations.append(v)
                seen.add(key)

    return {
        "violations": violations,
        "_model_used": True,
        "_latency_ms": latency_ms,
        "_tokens": _usage_tokens(response.usage),
    }
