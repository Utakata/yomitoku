"""
DSD Command-Line Interface.

Provides a user-friendly CLI for the Document Structure Deconstructor.
"""

import argparse
import logging
import sys
from pathlib import Path

from .orchestrator import DSDOrchestrator
from .models.cfg_layoutlmv3 import LayoutLMv3Config
from .models.cfg_vit import ViTConfig


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """
    Main CLI entry point for DSD.
    """
    parser = argparse.ArgumentParser(
        description="Document Structure Deconstructor (DSD) - Context Engineering 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  yomitoku-dsd input.pdf -o output/

  # With custom options
  yomitoku-dsd input.pdf -o output/ --min-split-level 2 --device cuda

  # Verbose mode
  yomitoku-dsd input.pdf -o output/ --verbose

For more information, visit: https://github.com/kotaro-kinoshita/yomitoku
        """,
    )

    # Required arguments
    parser.add_argument(
        "input",
        type=str,
        help="Input PDF file path",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory for generated Markdown files",
    )

    # DSD options
    parser.add_argument(
        "--min-split-level",
        type=int,
        default=3,
        help="Minimum TOC depth for splitting (default: 3). "
        "Nodes at or below this level will have separate Markdown files.",
    )

    parser.add_argument(
        "--figure-width",
        type=int,
        default=600,
        help="Figure display width in pixels (default: 600)",
    )

    parser.add_argument(
        "--keep-line-breaks",
        action="store_true",
        help="Keep line breaks within paragraphs (default: False)",
    )

    # Device options
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device for model inference (default: cuda)",
    )

    # Model options
    parser.add_argument(
        "--layoutlmv3-model",
        type=str,
        default=None,
        help="Path to fine-tuned LayoutLMv3 model (optional)",
    )

    parser.add_argument(
        "--vit-model",
        type=str,
        default=None,
        help="Path to fine-tuned ViT model (optional)",
    )

    # Yomitoku options
    parser.add_argument(
        "--reading-order",
        type=str,
        default="auto",
        choices=["auto", "left2right", "right2left", "top2bottom"],
        help="Reading order strategy (default: auto)",
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Enable visualization output (default: False)",
    )

    parser.add_argument(
        "--include-meta",
        action="store_true",
        help="Include page headers and footers (default: False)",
    )

    # Logging options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if not input_path.suffix.lower() == ".pdf":
        logger.error(f"Input file must be a PDF: {input_path}")
        sys.exit(1)

    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configure models
    layoutlmv3_config = LayoutLMv3Config(
        device=args.device,
        custom_model_path=args.layoutlmv3_model,
    )

    vit_config = ViTConfig(
        device=args.device,
        custom_model_path=args.vit_model,
    )

    try:
        # Initialize DSD Orchestrator
        logger.info("🤖 Document Structure Deconstructor (DSD) v1.0")
        logger.info("=" * 60)

        orchestrator = DSDOrchestrator(
            device=args.device,
            layoutlmv3_config=layoutlmv3_config,
            vit_config=vit_config,
            visualize=args.visualize,
            ignore_meta=not args.include_meta,
            reading_order=args.reading_order,
        )

        # Process PDF
        result = orchestrator.process_pdf(
            pdf_path=str(input_path),
            output_dir=str(output_path),
            min_split_level=args.min_split_level,
            figure_width=args.figure_width,
            ignore_line_break=not args.keep_line_breaks,
        )

        # Print final summary
        logger.info("=" * 60)
        logger.info("✅ DSD Processing Complete!")
        logger.info(f"📄 Source: {input_path.name}")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 Statistics:")
        logger.info(f"   - Pages: {result.statistics.get('total_pages', 0)}")
        logger.info(
            f"   - TOC Headings: {result.statistics.get('total_headings', 0)}"
        )
        logger.info(f"   - Paragraphs: {result.statistics.get('total_paragraphs', 0)}")
        logger.info(f"   - Tables: {result.statistics.get('total_tables', 0)}")
        logger.info(f"   - Diagrams: {result.statistics.get('total_diagrams', 0)}")
        logger.info(
            f"   - Textual Images: {result.statistics.get('total_textual_images', 0)}"
        )
        logger.info("=" * 60)

        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\nProcessing interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
