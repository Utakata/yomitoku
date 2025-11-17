"""
Content Transformer - transforms raw content into final representation.

This implements Step 5 of the DSD process: converting content into
low-entropy, machine-readable formats.
"""

import logging
from typing import List, Optional, Dict
import re

from yomitoku.schemas import TableStructureRecognizerSchema
from yomitoku.export.export_markdown import table_to_md, escape_markdown_special_chars
from .schemas import EnhancedParagraph, EnhancedFigure, LinkSchema

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

    def __init__(
        self,
        ignore_line_break: bool = True,
        link_registry: Optional[Dict[str, str]] = None,
        current_markdown_path: Optional[str] = None,
    ):
        """
        Initialize the content transformer.

        Args:
            ignore_line_break: If True, remove line breaks within paragraphs
            link_registry: Dictionary mapping anchor_id to Markdown file paths (for internal links)
            current_markdown_path: Current Markdown file path (for relative link calculation)
        """
        self.ignore_line_break = ignore_line_break
        self.link_registry = link_registry or {}
        self.current_markdown_path = current_markdown_path

    def _convert_links_to_markdown(
        self,
        content: str,
        links: List[LinkSchema],
    ) -> str:
        """
        Convert hyperlinks to Markdown format.

        Args:
            content: Text content
            links: List of links to convert

        Returns:
            Content with Markdown links
        """
        if not links:
            return content

        # Sort links by position (if bbox is available) to process from end to start
        # This prevents offset issues when inserting link markup
        for link in sorted(links, key=lambda l: l.bbox[0] if l.bbox else 0, reverse=True):
            if link.link_type == "external" and link.url:
                # External link: [text](url)
                link_text = link.text or link.url
                markdown_link = f"[{link_text}]({link.url})"

                # If we have bbox, try to find and replace the text
                if link.text and link.text in content:
                    content = content.replace(link.text, markdown_link, 1)
                else:
                    # Append link at the end if we can't find exact position
                    content += f" {markdown_link}"

            elif link.link_type == "internal":
                # Internal link: resolve using link_registry
                target_path = None

                # Try to resolve by anchor_id
                if link.target_anchor and link.target_anchor in self.link_registry:
                    target_path = self.link_registry[link.target_anchor]

                # If resolved, create relative link
                if target_path and self.current_markdown_path:
                    # Calculate relative path
                    from pathlib import Path
                    current_dir = Path(self.current_markdown_path).parent
                    target = Path(target_path)

                    try:
                        rel_path = target.relative_to(current_dir)
                    except ValueError:
                        # Not in same directory tree, use absolute path
                        rel_path = target

                    link_text = link.text or "link"
                    markdown_link = f"[{link_text}]({rel_path})"

                    if link.text and link.text in content:
                        content = content.replace(link.text, markdown_link, 1)
                    else:
                        content += f" {markdown_link}"

                else:
                    # Can't resolve, log warning
                    logger.warning(
                        f"Could not resolve internal link: anchor={link.target_anchor}, page={link.target_page}"
                    )

        return content

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

        # Convert hyperlinks to Markdown format
        if hasattr(paragraph, "links") and paragraph.links:
            content = self._convert_links_to_markdown(content, paragraph.links)

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
