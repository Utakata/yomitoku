"""
Vision Transformer (ViT) model configuration for image classification.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ViTConfig:
    """
    Configuration for ViT-based image classifier (Diagram vs Textual_Image).
    """

    model_name: str = "google/vit-base-patch16-224"
    """HuggingFace model identifier"""

    num_labels: int = 2
    """Number of classification labels:
    - 0: Diagram (visual information is valuable, keep as image)
    - 1: Textual_Image (text embedded in image, OCR to text)
    """

    image_size: int = 224
    """Input image size for ViT"""

    device: str = "cuda"
    """Device for model inference: 'cuda' or 'cpu'"""

    confidence_threshold: float = 0.6
    """Minimum confidence score for classification"""

    custom_model_path: Optional[str] = None
    """Path to fine-tuned model weights (if available)"""

    fallback_to_diagram: bool = True
    """If confidence is low, fallback to 'Diagram' (safer choice)"""
