"""
vision.py -- Gemini Vision Analysis for Campus Commander facility & equipment photos.

Features:
- Validates mime type and file size.
- Uses the backend's existing google-genai SDK client and GEMINI_API_KEY.
- Extracts structured issue, equipment, visible_damage, location, and confidence.
- Synthesizes a unified goal combining user text and visual diagnostic facts.
"""

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

VISION_SYSTEM_PROMPT = """You are Campus Commander's facility diagnostic vision agent.
Analyze the provided campus facility or equipment image and extract only facts relevant to campus maintenance.

You MUST return a valid, well-formed JSON object with EXACTLY these keys:
{
  "issue": "Concise summary of the problem or condition (e.g. 'Projector display shattered / broken lens')",
  "equipment": "Type of equipment identified (e.g. 'Projector', 'AC Unit', 'Computer Monitor', 'Light Fixture', etc.)",
  "visible_damage": "Specific visible damage or physical state (e.g. 'Cracked outer casing and internal lens fragmentation')",
  "location": "Room or facility identifier if visible on labels/signs, or null if unknown",
  "confidence": 0.95
}

Rules:
1. Do not hallucinate location unless visible on equipment label or wall plaque.
2. Return ONLY valid JSON. No markdown code blocks, no explanation text.
"""

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def synthesize_combined_goal(user_text: Optional[str], analysis: Dict[str, Any]) -> str:
    """
    Combines student's natural-language text with visual diagnostic facts into
    a unified, actionable goal for the existing agent planner.
    """
    user_part = (user_text or "").strip()
    issue = (analysis.get("issue") or "Equipment maintenance issue").strip()
    damage = (analysis.get("visible_damage") or "").strip()
    equipment = (analysis.get("equipment") or "equipment").strip()
    location = (analysis.get("location") or "").strip()

    details = []
    if damage and damage.lower() not in user_part.lower():
        details.append(f"Visual analysis indicates {damage}")
    elif issue and issue.lower() not in user_part.lower():
        details.append(f"Visual analysis indicates {issue}")

    if user_part:
        if details:
            combined = f"{user_part} Image analysis indicates: {', '.join(details)}."
        else:
            combined = user_part
    else:
        loc_str = f" in {location}" if location else ""
        damage_str = f" Visual inspection reveals {damage}." if damage else ""
        combined = f"The {equipment}{loc_str} has a maintenance issue: {issue}.{damage_str}"

    return combined.strip()


def analyze_facility_image(
    image_bytes: bytes,
    mime_type: str,
    user_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyzes an uploaded image with Gemini Vision and returns structured diagnostic data.
    """
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported image type '{mime_type}'. Supported formats: JPEG, PNG, WebP."
        )

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image file size exceeds the 10MB limit.")

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not configured in backend environment.")

    client = genai.Client(api_key=api_key)

    prompt = "Analyze this campus facility or equipment issue."
    if user_text and user_text.strip():
        prompt += f" Additional user context: \"{user_text.strip()}\""

    contents = [
        prompt,
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
    ]

    candidate_models = [model_name]
    for fallback in ("gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"):
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_exc = None
    for m in candidate_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=VISION_SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or ""
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
            return parsed
        except Exception as exc:
            last_exc = exc
            continue

    raise ValueError(f"All Gemini Vision models failed. Last error: {last_exc}") from last_exc
