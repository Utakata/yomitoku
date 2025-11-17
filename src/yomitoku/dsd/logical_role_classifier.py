"""
Logical Role Classifier using LayoutLMv3 for TOC hierarchy inference.

This module implements the "Left Brain" of DSD, inferring logical roles and
hierarchy levels from section headings.
"""

import re
import logging
import unicodedata
from typing import List, Optional, Dict, Any
import torch
import numpy as np

try:
    from transformers import (
        LayoutLMv3Processor,
        LayoutLMv3ForTokenClassification,
        LayoutLMv3ForSequenceClassification,
    )
    from PIL import Image

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from yomitoku.schemas import ParagraphSchema
from .schemas import EnhancedParagraph
from .models.cfg_layoutlmv3 import LayoutLMv3Config

logger = logging.getLogger(__name__)


class LogicalRoleClassifier:
    """
    Classifies paragraphs into logical roles with TOC hierarchy levels.

    Uses LayoutLMv3 for multimodal understanding of text, layout, and visual features
    to infer document structure.
    """

    # Label mapping
    LABEL_MAP = {
        0: {"logical_role": None, "toc_level": None},  # Not a heading
        1: {"logical_role": "Chapter_Title", "toc_level": 1},
        2: {"logical_role": "Section_Title", "toc_level": 2},
        3: {"logical_role": "Subsection_Title", "toc_level": 3},
        4: {"logical_role": "Subsubsection_Title", "toc_level": 4},
        5: {"logical_role": "Header", "toc_level": None},
        6: {"logical_role": "Footer", "toc_level": None},
    }

    def __init__(self, config: Optional[LayoutLMv3Config] = None):
        """
        Initialize the logical role classifier.

        Args:
            config: Configuration for LayoutLMv3 model
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers library is required for LayoutLMv3. "
                "Install it with: pip install transformers"
            )

        self.config = config or LayoutLMv3Config()
        self.device = torch.device(
            self.config.device if torch.cuda.is_available() else "cpu"
        )

        logger.info(f"Initializing LayoutLMv3 on device: {self.device}")

        # Load model and processor
        self._load_model()

    def _load_model(self):
        """Load LayoutLMv3 model and processor."""
        try:
            if self.config.custom_model_path:
                logger.info(
                    f"Loading fine-tuned model from: {self.config.custom_model_path}"
                )
                self.model = LayoutLMv3ForSequenceClassification.from_pretrained(
                    self.config.custom_model_path,
                    num_labels=self.config.num_labels,
                )
                self.processor = LayoutLMv3Processor.from_pretrained(
                    self.config.custom_model_path
                )
            else:
                logger.warning(
                    "No fine-tuned model provided. Using base model with heuristic fallback."
                )
                # For now, we'll use heuristic approach
                # In production, a fine-tuned model should be used
                self.model = None
                self.processor = None

        except Exception as e:
            logger.error(f"Failed to load LayoutLMv3 model: {e}")
            logger.warning("Falling back to rule-based heuristic classifier")
            self.model = None
            self.processor = None

    def _heuristic_classify(
        self, paragraph: ParagraphSchema, page_img: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Heuristic-based classification for when model is unavailable.

        This uses pattern matching and simple rules to infer hierarchy.

        Args:
            paragraph: Paragraph to classify
            page_img: Optional page image for visual features

        Returns:
            Dictionary with logical_role, toc_level, and toc_title
        """
        content = paragraph.contents.strip()

        # Handle existing roles from yomitoku
        if paragraph.role == "page_header":
            return {"logical_role": "Header", "toc_level": None, "toc_title": None}
        if paragraph.role == "page_footer":
            return {"logical_role": "Footer", "toc_level": None, "toc_title": None}

        # Pattern matching for Japanese TOC structures
        patterns = [
            # Chapter patterns (level 1)
            (r"^第?[0-9一二三四五六七八九十百千]+章\s*[：:：\s]?\s*(.+)", 1),
            (r"^第?[IVX]+章\s*[：:：\s]?\s*(.+)", 1),
            (r"^Chapter\s+\d+\s*[：:：\s]?\s*(.+)", 1),
            (r"^[0-9]+\.\s+([^0-9].+)", 1),  # "1. Introduction"
            # Section patterns (level 2)
            (r"^[0-9]+\.[0-9]+\s+(.+)", 2),  # "1.1 Overview"
            (r"^[0-9]+\.[0-9]+\s*[：:：]\s*(.+)", 2),  # "1.1: Overview"
            # Subsection patterns (level 3)
            (r"^[0-9]+\.[0-9]+\.[0-9]+\s+(.+)", 3),  # "1.1.1 Details"
            (r"^[0-9]+\.[0-9]+\.[0-9]+\s*[：:：]\s*(.+)", 3),
            # Subsubsection patterns (level 4)
            (r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\s+(.+)", 4),
        ]

        for pattern, level in patterns:
            match = re.match(pattern, content)
            if match:
                title = content  # Keep full title
                role_map = {
                    1: "Chapter_Title",
                    2: "Section_Title",
                    3: "Subsection_Title",
                    4: "Subsubsection_Title",
                }
                return {
                    "logical_role": role_map.get(level),
                    "toc_level": level,
                    "toc_title": title,
                }

        # If marked as section_headings but no pattern matched, try to infer from context
        if paragraph.role == "section_headings":
            # Assume it's a section heading, default to level 2
            return {
                "logical_role": "Section_Title",
                "toc_level": 2,
                "toc_title": content,
            }

        # Not a heading
        return {"logical_role": None, "toc_level": None, "toc_title": None}

    def _model_classify(
        self, paragraph: ParagraphSchema, page_img: Optional[Image.Image] = None
    ) -> Dict[str, Any]:
        """
        Model-based classification using LayoutLMv3.

        Args:
            paragraph: Paragraph to classify
            page_img: Optional page image for visual features

        Returns:
            Dictionary with logical_role, toc_level, and toc_title
        """
        if self.model is None or self.processor is None:
            return self._heuristic_classify(paragraph, page_img)

        try:
            # Prepare inputs
            text = paragraph.contents.strip()
            bbox = paragraph.box  # [x1, y1, x2, y2]

            # Normalize bbox to [0, 1000] scale (LayoutLMv3 convention)
            # This would require page dimensions, for now use as-is
            # In production, normalize properly

            encoding = self.processor(
                text,
                boxes=[bbox],
                images=page_img if self.config.use_visual_features else None,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_length,
            )

            # Move to device
            encoding = {k: v.to(self.device) for k, v in encoding.items()}

            # Inference
            with torch.no_grad():
                outputs = self.model(**encoding)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                predicted_class = torch.argmax(probs, dim=-1).item()
                confidence = probs[0, predicted_class].item()

            # Check confidence threshold
            if confidence < self.config.confidence_threshold:
                logger.debug(
                    f"Low confidence ({confidence:.2f}), falling back to heuristic"
                )
                return self._heuristic_classify(paragraph, page_img)

            # Map prediction to result
            result = self.LABEL_MAP.get(predicted_class, self.LABEL_MAP[0]).copy()
            if result["toc_level"] is not None:
                result["toc_title"] = text

            return result

        except Exception as e:
            logger.error(f"Model classification failed: {e}. Using heuristic fallback.")
            return self._heuristic_classify(paragraph, page_img)

    def _generate_anchor_id(self, title: str) -> str:
        """
        Generate a URL-safe anchor ID from a title.

        Args:
            title: Title text (e.g., "第1章 導入", "1.1 概要")

        Returns:
            Anchor ID (e.g., "第1章-導入", "1-1-概要")
        """
        # Remove leading/trailing whitespace
        title = title.strip()

        # Replace spaces and special characters with hyphens
        # Keep alphanumeric, Japanese characters, and some punctuation
        anchor = re.sub(r'[\s_]+', '-', title)
        anchor = re.sub(r'[^\w\-\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', anchor)

        # Remove consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)

        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')

        # If empty after sanitization, use a fallback
        if not anchor:
            anchor = "section"

        return anchor

    def classify(
        self,
        paragraph: ParagraphSchema,
        page_img: Optional[Any] = None,
    ) -> EnhancedParagraph:
        """
        Classify a single paragraph to infer its logical role and TOC level.

        Args:
            paragraph: Paragraph from yomitoku DocumentAnalyzer
            page_img: Optional page image (numpy array or PIL Image)

        Returns:
            EnhancedParagraph with logical_role, toc_level, and toc_title
        """
        # Convert numpy array to PIL Image if needed
        if page_img is not None and isinstance(page_img, np.ndarray):
            page_img = Image.fromarray(page_img)

        # Perform classification
        classification = (
            self._model_classify(paragraph, page_img)
            if self.model is not None
            else self._heuristic_classify(paragraph, page_img)
        )

        # Generate anchor ID if this is a heading
        anchor_id = None
        if classification["toc_level"] is not None and classification["toc_title"]:
            anchor_id = self._generate_anchor_id(classification["toc_title"])

        # Create enhanced paragraph
        enhanced = EnhancedParagraph(
            box=paragraph.box,
            contents=paragraph.contents,
            direction=paragraph.direction,
            order=paragraph.order,
            role=paragraph.role,
            toc_level=classification["toc_level"],
            toc_title=classification["toc_title"],
            logical_role=classification["logical_role"],
            anchor_id=anchor_id,
            links=[],  # Will be populated by link extractor
        )

        return enhanced

    def classify_batch(
        self,
        paragraphs: List[ParagraphSchema],
        page_img: Optional[Any] = None,
    ) -> List[EnhancedParagraph]:
        """
        Classify multiple paragraphs.

        Args:
            paragraphs: List of paragraphs from yomitoku
            page_img: Optional page image

        Returns:
            List of EnhancedParagraphs
        """
        return [self.classify(p, page_img) for p in paragraphs]

    def __call__(
        self,
        paragraphs: List[ParagraphSchema],
        page_img: Optional[Any] = None,
    ) -> List[EnhancedParagraph]:
        """Convenience method for batch classification."""
        return self.classify_batch(paragraphs, page_img)
