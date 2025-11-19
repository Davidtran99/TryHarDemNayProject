"""
Optional PaddleOCR integration to improve OCR accuracy for legal documents.

This module is loaded lazily to avoid importing heavy dependencies when
the feature is disabled. To enable PaddleOCR, set the environment variable
``PADDLE_OCR_ENABLED=1`` before running ingestion scripts.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class PaddleOCRExtractor:
    """
    Wrapper around PaddleOCR to provide a simple API for extracting text lines.

    Usage:
        extractor = PaddleOCRExtractor.get_instance()
        if extractor:
            text = extractor.recognize_image(pil_image)
    """

    _instance: Optional["PaddleOCRExtractor"] = None
    _ocr_engine = None
    _failed = False

    def __init__(self):
        try:
            from paddleocr import PaddleOCR  # type: ignore

            lang = os.getenv("PADDLE_OCR_LANG", "en")
            use_gpu = os.getenv("PADDLE_OCR_USE_GPU", "0") == "1"

            candidate_kwargs = {
                "use_angle_cls": True,
                "lang": lang,
                "use_gpu": use_gpu,
                "show_log": os.getenv("PADDLE_OCR_SHOW_LOG", "0") == "1",
            }
            supported_params = set(inspect.signature(PaddleOCR).parameters.keys())
            kwargs = {
                key: value
                for key, value in candidate_kwargs.items()
                if key in supported_params
            }

            self._ocr = PaddleOCR(**kwargs)
            logger.info("✅ PaddleOCR initialized with args: %s", kwargs)
        except Exception as exc:  # pragma: no cover - import errors depend on env
            logger.warning("⚠️ PaddleOCR unavailable: %s", exc)
            self._ocr = None

    @classmethod
    def get_instance(cls) -> Optional["PaddleOCRExtractor"]:
        """Return a shared instance if PaddleOCR is available."""
        if cls._failed:
            return None

        if cls._instance is None:
            instance = cls()
            if instance._ocr is None:
                cls._failed = True
                return None
            cls._instance = instance
        return cls._instance

    def recognize_image(self, image: Image.Image) -> str:
        """
        Run OCR on a PIL image and return concatenated text lines.

        Args:
            image: PIL image (RGB/L) containing the document region.

        Returns:
            Recognized text separated by newlines.
        """
        if not self._ocr:
            return ""

        np_image = np.array(image.convert("RGB"))
        try:
            result = self._ocr.ocr(np_image)
        except Exception as exc:  # pragma: no cover - runtime errors depend on env
            logger.warning("PaddleOCR recognition failed: %s", exc)
            return ""

        lines: List[str] = []
        if isinstance(result, list):
            for page in result:
                for entry in page:
                    if len(entry) >= 2:
                        text = entry[1][0]
                        if text:
                            lines.append(text)
        return "\n".join(lines)


