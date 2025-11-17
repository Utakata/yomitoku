"""
Simple DSD (Document Structure Deconstructor) Demo

This demo shows how to use DSD to transform a PDF document into
a structured Markdown dataset with TOC-based organization.
"""

import logging
from pathlib import Path

from yomitoku.dsd import DSDOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """
    Simple DSD demonstration.
    """
    logger.info("=" * 60)
    logger.info("🤖 Document Structure Deconstructor (DSD) Demo")
    logger.info("=" * 60)

    # Configuration
    pdf_path = "sample.pdf"  # Replace with your PDF file
    output_dir = "output_dsd"

    # Check if PDF exists
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        logger.info("Please provide a PDF file and update the 'pdf_path' variable.")
        return

    # Initialize DSD Orchestrator
    logger.info("\n📋 Initializing DSD components...")
    logger.info("   - yomitoku DocumentAnalyzer")
    logger.info("   - LayoutLMv3 (TOC hierarchy inference)")
    logger.info("   - ViT (Image classification)")

    orchestrator = DSDOrchestrator(
        device="cpu",  # Use "cuda" if GPU is available
        visualize=False,
        ignore_meta=True,  # Ignore page headers/footers
        reading_order="auto",
    )

    # Process PDF
    logger.info("\n📄 Processing PDF...")
    logger.info(f"   Input: {pdf_path}")
    logger.info(f"   Output: {output_dir}")

    result = orchestrator.process_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        min_split_level=3,  # Split at level 3 and above
        figure_width=600,
        ignore_line_break=True,
    )

    # Display results
    logger.info("\n✅ Processing complete!")
    logger.info("\n📊 Statistics:")
    logger.info(f"   - Total Pages: {result.statistics.get('total_pages', 0)}")
    logger.info(f"   - TOC Headings: {result.statistics.get('total_headings', 0)}")
    logger.info(f"   - Paragraphs: {result.statistics.get('total_paragraphs', 0)}")
    logger.info(f"   - Tables: {result.statistics.get('total_tables', 0)}")
    logger.info(f"   - Figures: {result.statistics.get('total_figures', 0)}")
    logger.info(
        f"     - Diagrams (kept as images): {result.statistics.get('total_diagrams', 0)}"
    )
    logger.info(
        f"     - Textual Images (OCR to text): {result.statistics.get('total_textual_images', 0)}"
    )

    logger.info(f"\n📁 Output directory: {output_dir}")
    logger.info("   Check the directory for:")
    logger.info("   - Markdown files with TOC-based structure")
    logger.info("   - YAML Frontmatter with metadata")
    logger.info("   - media/ folder with diagram images")
    logger.info("   - structural_map.json")

    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    main()
