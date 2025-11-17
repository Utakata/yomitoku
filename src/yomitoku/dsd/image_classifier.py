"""
Image Classifier using Vision Transformer (ViT) for semantic classification.

This module implements the "Right Brain" of DSD, classifying figures as
"Diagram" (keep as image) or "Textual_Image" (OCR to text).
"""

import logging
from typing import List, Optional, Any
import torch
import numpy as np

try:
    from transformers import ViTImageProcessor, ViTForImageClassification
    from PIL import Image

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from yomitoku.schemas import FigureSchema
from .schemas import EnhancedFigure
from .models.cfg_vit import ViTConfig

logger = logging.getLogger(__name__)


class ImageClassifier:
    """
    Classifies figure images as Diagram or Textual_Image.

    Uses Vision Transformer (ViT) for visual understanding to determine
    whether a figure should be kept as an image or converted to text via OCR.
    """

    # Label mapping
    LABEL_MAP = {
        0: "Diagram",  # Visual information is valuable, keep as image
        1: "Textual_Image",  # Text embedded in image, should OCR to text
    }

    def __init__(self, config: Optional[ViTConfig] = None):
        """
        Initialize the image classifier.

        Args:
            config: Configuration for ViT model
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers library is required for ViT. "
                "Install it with: pip install transformers"
            )

        self.config = config or ViTConfig()
        self.device = torch.device(
            self.config.device if torch.cuda.is_available() else "cpu"
        )

        logger.info(f"Initializing ViT on device: {self.device}")

        # Load model and processor
        self._load_model()

    def _load_model(self):
        """Load ViT model and image processor."""
        try:
            if self.config.custom_model_path:
                logger.info(
                    f"Loading fine-tuned ViT model from: {self.config.custom_model_path}"
                )
                self.model = ViTForImageClassification.from_pretrained(
                    self.config.custom_model_path,
                    num_labels=self.config.num_labels,
                )
                self.processor = ViTImageProcessor.from_pretrained(
                    self.config.custom_model_path
                )
            else:
                logger.warning(
                    "No fine-tuned ViT model provided. Using heuristic fallback."
                )
                # For now, we'll use heuristic approach
                # In production, a fine-tuned model should be used
                self.model = None
                self.processor = None

        except Exception as e:
            logger.error(f"Failed to load ViT model: {e}")
            logger.warning("Falling back to heuristic classifier")
            self.model = None
            self.processor = None

    def _heuristic_classify(
        self, figure_img: np.ndarray, figure: FigureSchema
    ) -> str:
        """
        Heuristic-based classification for when model is unavailable.

        This uses simple rules to make educated guesses:
        - If figure contains paragraphs (text detected by yomitoku), likely Textual_Image
        - Otherwise, assume Diagram (safer default)

        Args:
            figure_img: Figure image as numpy array
            figure: FigureSchema with metadata

        Returns:
            "Diagram" or "Textual_Image"
        """
        # Check if figure has paragraphs (text detected inside)
        if hasattr(figure, "paragraphs") and len(figure.paragraphs) > 0:
            # Calculate text density
            total_text_length = sum(
                len(p.contents) for p in figure.paragraphs if p.contents
            )

            # If there's substantial text content, likely a textual image
            if total_text_length > 50:  # Threshold for "substantial text"
                logger.debug(
                    f"Figure has {total_text_length} chars of text, classifying as Textual_Image"
                )
                return "Textual_Image"

        # Default to Diagram (safer choice - keeps visual information)
        logger.debug("No substantial text detected, classifying as Diagram")
        return "Diagram"

    def _model_classify(self, figure_img: Image.Image) -> str:
        """
        Model-based classification using ViT.

        Args:
            figure_img: Figure image as PIL Image

        Returns:
            "Diagram" or "Textual_Image"
        """
        if self.model is None or self.processor is None:
            # Convert PIL to numpy for heuristic
            return self._heuristic_classify(np.array(figure_img), None)

        try:
            # Preprocess image
            inputs = self.processor(
                images=figure_img, return_tensors="pt", size=self.config.image_size
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                predicted_class = torch.argmax(probs, dim=-1).item()
                confidence = probs[0, predicted_class].item()

            # Check confidence threshold
            if confidence < self.config.confidence_threshold:
                logger.debug(
                    f"Low confidence ({confidence:.2f}) for ViT classification"
                )
                if self.config.fallback_to_diagram:
                    logger.debug("Falling back to 'Diagram' (safe default)")
                    return "Diagram"

            # Map prediction to label
            semantic_type = self.LABEL_MAP.get(predicted_class, "Diagram")
            logger.debug(
                f"ViT classified as '{semantic_type}' with confidence {confidence:.2f}"
            )

            return semantic_type

        except Exception as e:
            logger.error(f"ViT classification failed: {e}. Using heuristic fallback.")
            return self._heuristic_classify(np.array(figure_img), None)

    def classify(
        self,
        figure: FigureSchema,
        page_img: np.ndarray,
    ) -> EnhancedFigure:
        """
        Classify a single figure to determine its semantic type.

        Args:
            figure: FigureSchema from yomitoku
            page_img: Full page image as numpy array

        Returns:
            EnhancedFigure with semantic_type classification
        """
        # Extract figure region from page image
        x1, y1, x2, y2 = map(int, figure.box)
        figure_img = page_img[y1:y2, x1:x2, :]

        # Convert to PIL Image
        if isinstance(figure_img, np.ndarray):
            figure_img_pil = Image.fromarray(figure_img)
        else:
            figure_img_pil = figure_img

        # Perform classification
        if self.model is not None:
            semantic_type = self._model_classify(figure_img_pil)
        else:
            semantic_type = self._heuristic_classify(figure_img, figure)

        # Create enhanced figure
        enhanced = EnhancedFigure(
            box=figure.box,
            order=figure.order,
            paragraphs=figure.paragraphs,
            direction=figure.direction,
            semantic_type=semantic_type,
            ocr_text=None,  # Will be populated later if Textual_Image
        )

        return enhanced

    def classify_batch(
        self,
        figures: List[FigureSchema],
        page_img: np.ndarray,
    ) -> List[EnhancedFigure]:
        """
        Classify multiple figures.

        Args:
            figures: List of FigureSchema from yomitoku
            page_img: Full page image

        Returns:
            List of EnhancedFigures with classifications
        """
        return [self.classify(fig, page_img) for fig in figures]

    def __call__(
        self,
        figures: List[FigureSchema],
        page_img: np.ndarray,
    ) -> List[EnhancedFigure]:
        """Convenience method for batch classification."""
        return self.classify_batch(figures, page_img)
