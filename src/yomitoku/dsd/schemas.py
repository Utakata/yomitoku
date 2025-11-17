"""
DSD-specific schemas for structured document representation.
"""

from typing import List, Union, Optional, Dict, Any
from pydantic import Field

from yomitoku.base import BaseSchema
from yomitoku.schemas import ParagraphSchema, FigureSchema, TableStructureRecognizerSchema


class EnhancedParagraph(ParagraphSchema):
    """
    Extended paragraph schema with TOC hierarchy information.
    """

    toc_level: Optional[int] = Field(
        None,
        description="TOC hierarchy level (1 for chapter, 2 for section, etc.)",
    )
    toc_title: Optional[str] = Field(
        None,
        description="Cleaned TOC title extracted from content",
    )
    logical_role: Optional[str] = Field(
        None,
        description="Logical role: 'Chapter_Title', 'Section_Title', 'Paragraph', 'Header', 'Footer'",
    )


class EnhancedFigure(FigureSchema):
    """
    Extended figure schema with semantic classification.
    """

    semantic_type: Optional[str] = Field(
        None,
        description="Semantic type: 'Diagram' (keep as image) or 'Textual_Image' (OCR to text)",
    )
    ocr_text: Optional[str] = Field(
        None,
        description="OCR text if semantic_type is 'Textual_Image'",
    )


class TOCNode(BaseSchema):
    """
    A node in the TOC (Table of Contents) hierarchy tree.
    """

    level: int = Field(
        ...,
        description="Hierarchy level (1 for chapter, 2 for section, etc.)",
    )
    title: str = Field(
        ...,
        description="Node title (e.g., '第1章 導入', '1.1 概要')",
    )
    content_blocks: List[str] = Field(
        default_factory=list,
        description="List of content block IDs associated with this node (paragraphs, tables, figures)",
    )
    children: List["TOCNode"] = Field(
        default_factory=list,
        description="Child TOC nodes",
    )
    parent_title: Optional[str] = Field(
        None,
        description="Parent node title for metadata",
    )
    order: int = Field(
        ...,
        description="Sequential order in document",
    )


class StructuralMap(BaseSchema):
    """
    The persistent memory structure representing document hierarchy.
    This is the 'self-baked' context that enables TOC-based operations.
    """

    title: str = Field(
        ...,
        description="Document title",
    )
    source_document: str = Field(
        ...,
        description="Original PDF filename",
    )
    nodes: List[TOCNode] = Field(
        ...,
        description="Root-level TOC nodes",
    )
    content_registry: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Registry mapping block IDs to actual content (paragraphs, tables, figures)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata",
    )


class DSDResult(BaseSchema):
    """
    Final result of DSD processing.
    """

    structural_map: StructuralMap = Field(
        ...,
        description="The constructed structural map",
    )
    enhanced_paragraphs: List[EnhancedParagraph] = Field(
        ...,
        description="All paragraphs with TOC hierarchy information",
    )
    enhanced_figures: List[EnhancedFigure] = Field(
        ...,
        description="All figures with semantic classification",
    )
    tables: List[TableStructureRecognizerSchema] = Field(
        ...,
        description="All tables from document analysis",
    )
    statistics: Dict[str, int] = Field(
        default_factory=dict,
        description="Processing statistics",
    )
