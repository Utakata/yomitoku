"""
Content Transformer - transforms raw content into final representation.

This implements Step 5 of the DSD process: converting content into
low-entropy, machine-readable formats.
"""

import logging
from typing import List, Optional
import re

from yomitoku.schemas import TableStructureRecognizerSchema
from yomitoku.export.export_markdown import table_to_md, escape_markdown_special_chars
from .schemas import EnhancedParagraph, EnhancedFigure

logger = logging.getLogger(__name__)


class ContentTransformer:
    """
    Transforms content blocks into final representation for Markdown output.

    Key transformations:
    - Textual_Image figures → OCR text
    - Diagram figures → preserve as image reference
    - Tables → Markdown table format
    - Paragraphs → cleaned text with proper formatting
    """

    def __init__(self, ignore_line_break: bool = True):
        """
        Initialize the content transformer.

        Args:
            ignore_line_break: If True, remove line breaks within paragraphs
        """
        self.ignore_line_break = ignore_line_break

    def transform_paragraph(self, paragraph: EnhancedParagraph) -> str:
        """
        Transform a paragraph into Markdown text.

        Args:
            paragraph: EnhancedParagraph to transform

        Returns:
            Markdown-formatted text
        """
        if not paragraph.contents:
            return ""

        content = paragraph.contents.strip()

        # Escape markdown special characters
        content = escape_markdown_special_chars(content)

        # Handle line breaks
        if self.ignore_line_break:
            content = content.replace("\n", " ")
        else:
            content = content.replace("\n", "  \n")  # Markdown line break

        # Handle logical roles
        if paragraph.logical_role in ["Chapter_Title", "Section_Title", "Subsection_Title", "Subsubsection_Title"]:
            # These are already handled as TOC nodes, shouldn't appear here
            # But if they do, format as headers
            level = paragraph.toc_level or 1
            header_prefix = "#" * min(level, 6)
            return f"{header_prefix} {content}\n\n"

        # Handle section_headings role from yomitoku
        if paragraph.role == "section_headings" and not paragraph.toc_level:
            # Fallback heading that wasn't classified as TOC
            return f"## {content}\n\n"

        # Regular paragraph
        return f"{content}\n\n"

    def transform_table(
        self, table: TableStructureRecognizerSchema
    ) -> str:
        """
        Transform a table into Markdown table format.

        Args:
            table: TableStructureRecognizerSchema to transform

        Returns:
            Markdown-formatted table
        """
        try:
            result = table_to_md(table, self.ignore_line_break)
            return result["md"] + "\n"
        except Exception as e:
            logger.error(f"Failed to convert table to markdown: {e}")
            return f"\n*[Table conversion error: {str(e)}]*\n\n"

    def transform_figure_to_text(
        self, figure: EnhancedFigure
    ) -> str:
        """
        Transform a Textual_Image figure into OCR text.

        Args:
            figure: EnhancedFigure classified as Textual_Image

        Returns:
            OCR text content
        """
        if figure.ocr_text:
            # OCR text was already extracted
            text = figure.ocr_text.strip()
            text = escape_markdown_special_chars(text)
            if self.ignore_line_break:
                text = text.replace("\n", " ")
            else:
                text = text.replace("\n", "  \n")
            return f"{text}\n\n"

        # Fallback: extract from figure paragraphs
        if figure.paragraphs:
            paragraphs_text = []
            for para in sorted(figure.paragraphs, key=lambda p: p.order):
                if para.contents:
                    text = para.contents.strip()
                    text = escape_markdown_special_chars(text)
                    paragraphs_text.append(text)

            combined = " ".join(paragraphs_text) if self.ignore_line_break else "\n".join(paragraphs_text)
            return f"{combined}\n\n"

        logger.warning(f"Textual_Image at order {figure.order} has no OCR text or paragraphs")
        return ""

    def create_figure_reference(
        self,
        figure: EnhancedFigure,
        figure_path: str,
        width: int = 600,
    ) -> str:
        """
        Create a Markdown image reference for a Diagram figure.

        Args:
            figure: EnhancedFigure classified as Diagram
            figure_path: Relative path to the saved figure image
            width: Image width in pixels for display

        Returns:
            Markdown image reference
        """
        # Extract caption from figure paragraphs if available
        caption = ""
        if figure.paragraphs:
            # Use first paragraph as caption
            caption = figure.paragraphs[0].contents.strip()
            if len(caption) > 100:
                caption = caption[:100] + "..."

        if not caption:
            caption = f"Figure (order {figure.order})"

        # Create markdown image with HTML for width control
        md = f'<img src="{figure_path}" alt="{caption}" width="{width}px">\n\n'

        # Add caption as italic text
        if caption:
            md += f"*{escape_markdown_special_chars(caption)}*\n\n"

        return md

    def transform_content_block(
        self,
        content_type: str,
        content: any,
        figure_path: Optional[str] = None,
    ) -> str:
        """
        Transform any content block into Markdown text.

        Args:
            content_type: Type of content ('paragraph', 'table', 'figure')
            content: The content object
            figure_path: Path to figure image (if content_type is 'figure' and it's a Diagram)

        Returns:
            Markdown-formatted text
        """
        if content_type == "paragraph":
            return self.transform_paragraph(content)

        elif content_type == "table":
            return self.transform_table(content)

        elif content_type == "figure":
            figure = content
            if figure.semantic_type == "Textual_Image":
                return self.transform_figure_to_text(figure)
            elif figure.semantic_type == "Diagram":
                if not figure_path:
                    logger.warning(f"Diagram figure at order {figure.order} has no figure_path")
                    return f"\n*[Figure: {figure_path or 'missing path'}]*\n\n"
                return self.create_figure_reference(figure, figure_path)
            else:
                # Unknown semantic type, treat as diagram for safety
                logger.warning(f"Unknown semantic_type '{figure.semantic_type}' for figure at order {figure.order}")
                if figure_path:
                    return self.create_figure_reference(figure, figure_path)
                return ""

        else:
            logger.error(f"Unknown content type: {content_type}")
            return ""

    def __call__(
        self,
        content_type: str,
        content: any,
        figure_path: Optional[str] = None,
    ) -> str:
        """Convenience method for transformation."""
        return self.transform_content_block(content_type, content, figure_path)
