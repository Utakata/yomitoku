"""
DSD-specific schemas for structured document representation.
"""

from typing import List, Union, Optional, Dict, Any
from pydantic import Field

from yomitoku.base import BaseSchema
from yomitoku.schemas import ParagraphSchema, FigureSchema, TableStructureRecognizerSchema


class LinkSchema(BaseSchema):
    """
    Hyperlink information extracted from PDF.
    """

    link_type: str = Field(
        ...,
        description="Type of link: 'external' (URL) or 'internal' (anchor/page reference)",
    )
    url: Optional[str] = Field(
        None,
        description="URL for external links",
    )
    target_page: Optional[int] = Field(
        None,
        description="Target page number for internal links (0-indexed)",
    )
    target_anchor: Optional[str] = Field(
        None,
        description="Target anchor ID for internal links",
    )
    text: Optional[str] = Field(
        None,
        description="Link text (if available)",
    )
    bbox: Optional[List[float]] = Field(
        None,
        description="Bounding box of the link [x1, y1, x2, y2]",
    )


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
    anchor_id: Optional[str] = Field(
        None,
        description="Anchor ID for this paragraph (used for internal link resolution)",
    )
    links: List[LinkSchema] = Field(
        default_factory=list,
        description="List of hyperlinks found in this paragraph",
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
    anchor_id: Optional[str] = Field(
        None,
        description="Anchor ID for this TOC node (used for internal link resolution)",
    )
    markdown_path: Optional[str] = Field(
        None,
        description="Relative path to the Markdown file for this node",
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
    link_registry: Dict[str, str] = Field(
        default_factory=dict,
        description="Registry mapping internal link targets (page_num or anchor_id) to Markdown file paths",
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
