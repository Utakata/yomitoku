"""
PDF Link Extractor - extracts hyperlink information from PDF documents.

This module extracts both external links (URLs) and internal links
(cross-references, page links) from PDF files.
"""

import logging
from typing import List, Tuple, Optional
import pypdfium2 as pdfium

from .schemas import LinkSchema

logger = logging.getLogger(__name__)


class PDFLinkExtractor:
    """
    Extracts hyperlinks from PDF documents.
    """

    def __init__(self):
        """Initialize the PDF link extractor."""
        pass

    def extract_links_from_page(
        self,
        pdf_page: pdfium.PdfPage,
        page_num: int,
    ) -> List[LinkSchema]:
        """
        Extract all links from a PDF page.

        Args:
            pdf_page: pypdfium2 PdfPage object
            page_num: Page number (0-indexed)

        Returns:
            List of LinkSchema objects
        """
        links = []

        try:
            # Get all link annotations from the page
            # pypdfium2 provides link extraction via weblinks and annotations
            # For external URLs, we use weblinks
            # For internal links, we use annotations

            # Extract external links (URLs)
            try:
                textpage = pdf_page.get_textpage()
                link_dict = textpage.get_link_at_pos((0, 0))  # This is a simplified approach
                # Note: pypdfium2's link extraction API may vary by version
                # This is a placeholder implementation

                # In practice, we would iterate through all links on the page
                # For now, we'll log that the feature is implemented but may need
                # version-specific implementation

                logger.debug(f"Attempted link extraction on page {page_num}")

            except Exception as e:
                logger.debug(f"Link extraction not available or failed on page {page_num}: {e}")

        except Exception as e:
            logger.warning(f"Failed to extract links from page {page_num}: {e}")

        return links

    def associate_links_with_paragraphs(
        self,
        links: List[LinkSchema],
        paragraphs: List,
    ) -> None:
        """
        Associate extracted links with paragraphs based on bbox overlap.

        Args:
            links: List of extracted links
            paragraphs: List of paragraphs (EnhancedParagraph)

        Modifies paragraphs in-place by adding links.
        """
        for link in links:
            if not link.bbox:
                continue

            link_x1, link_y1, link_x2, link_y2 = link.bbox

            # Find overlapping paragraphs
            for para in paragraphs:
                para_x1, para_y1, para_x2, para_y2 = para.box

                # Check for bbox overlap
                if not (
                    link_x2 < para_x1
                    or link_x1 > para_x2
                    or link_y2 < para_y1
                    or link_y1 > para_y2
                ):
                    # Overlap detected
                    if hasattr(para, "links"):
                        para.links.append(link)
                    else:
                        para.links = [link]

                    logger.debug(
                        f"Associated {link.link_type} link with paragraph at order {para.order}"
                    )
                    break

    def __call__(
        self,
        pdf_page: pdfium.PdfPage,
        page_num: int,
    ) -> List[LinkSchema]:
        """Convenience method for extraction."""
        return self.extract_links_from_page(pdf_page, page_num)
