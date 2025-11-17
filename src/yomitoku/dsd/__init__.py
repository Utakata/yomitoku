"""
Document Structure Deconstructor (DSD)

A Context Engineering 2.0 compliant system for transforming high-entropy PDF documents
into low-entropy structured datasets with TOC-based hierarchical organization.
"""

from .schemas import (
    TOCNode,
    StructuralMap,
    EnhancedParagraph,
    EnhancedFigure,
    DSDResult,
)
from .structural_map import StructuralMapBuilder
from .markdown_generator import TOCMarkdownGenerator

__all__ = [
    "TOCNode",
    "StructuralMap",
    "EnhancedParagraph",
    "EnhancedFigure",
    "DSDResult",
    "StructuralMapBuilder",
    "TOCMarkdownGenerator",
]
