"""
LayoutLMv3 model configuration for TOC hierarchy inference.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LayoutLMv3Config:
    """
    Configuration for LayoutLMv3-based logical role classifier.
    """

    model_name: str = "microsoft/layoutlmv3-base"
    """HuggingFace model identifier"""

    num_labels: int = 7
    """Number of classification labels:
    - 0: Not a heading (null)
    - 1: Chapter_Title (level 1)
    - 2: Section_Title (level 2)
    - 3: Subsection_Title (level 3)
    - 4: Subsubsection_Title (level 4)
    - 5: Header (page_header)
    - 6: Footer (page_footer)
    """

    max_length: int = 512
    """Maximum sequence length for tokenizer"""

    device: str = "cuda"
    """Device for model inference: 'cuda' or 'cpu'"""

    confidence_threshold: float = 0.7
    """Minimum confidence score for classification"""

    custom_model_path: Optional[str] = None
    """Path to fine-tuned model weights (if available)"""

    use_visual_features: bool = True
    """Whether to use visual features (bbox, image) for inference"""
