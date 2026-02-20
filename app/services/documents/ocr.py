from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OCRResult:
    text: str
    confidence: float


def extract_text_locally(_pdf_bytes: bytes) -> OCRResult:
    return OCRResult(text="", confidence=0.0)
