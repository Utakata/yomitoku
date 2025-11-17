"""
DSD Orchestrator - coordinates all DSD components.

This is the main entry point for the Document Structure Deconstructor,
implementing the complete Context Engineering 2.0 pipeline.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import pypdfium2 as pdfium

from yomitoku.document_analyzer import DocumentAnalyzer
from .logical_role_classifier import LogicalRoleClassifier
from .image_classifier import ImageClassifier
from .structural_map import StructuralMapBuilder
from .markdown_generator import TOCMarkdownGenerator
from .pdf_link_extractor import PDFLinkExtractor
from .schemas import DSDResult
from .models.cfg_layoutlmv3 import LayoutLMv3Config
from .models.cfg_vit import ViTConfig

logger = logging.getLogger(__name__)


class DSDOrchestrator:
    """
    Orchestrates the complete DSD pipeline.

    This is the Initiative Agent that coordinates all components to transform
    high-entropy PDFs into low-entropy structured datasets.
    """

    def __init__(
        self,
        device: str = "cuda",
        layoutlmv3_config: Optional[LayoutLMv3Config] = None,
        vit_config: Optional[ViTConfig] = None,
        visualize: bool = False,
        ignore_meta: bool = True,
        reading_order: str = "auto",
    ):
        """
        Initialize the DSD orchestrator.

        Args:
            device: Device for model inference ('cuda' or 'cpu')
            layoutlmv3_config: Configuration for LayoutLMv3
            vit_config: Configuration for ViT
            visualize: Enable visualization output
            ignore_meta: Ignore page headers/footers
            reading_order: Reading order strategy ('auto', 'left2right', 'right2left', 'top2bottom')
        """
        logger.info("Initializing Document Structure Deconstructor...")

        # Initialize yomitoku DocumentAnalyzer
        logger.info("Initializing yomitoku DocumentAnalyzer...")
        self.document_analyzer = DocumentAnalyzer(
            device=device,
            visualize=visualize,
            ignore_meta=ignore_meta,
            reading_order=reading_order,
        )

        # Initialize DSD components
        logger.info("Initializing DSD components...")

        # LogicalRoleClassifier (LayoutLMv3)
        try:
            layoutlmv3_cfg = layoutlmv3_config or LayoutLMv3Config(device=device)
            self.logical_classifier = LogicalRoleClassifier(config=layoutlmv3_cfg)
        except Exception as e:
            logger.warning(f"Failed to initialize LayoutLMv3: {e}")
            logger.warning("Will use heuristic-based classification")
            self.logical_classifier = LogicalRoleClassifier(
                config=LayoutLMv3Config(device=device)
            )

        # ImageClassifier (ViT)
        try:
            vit_cfg = vit_config or ViTConfig(device=device)
            self.image_classifier = ImageClassifier(config=vit_cfg)
        except Exception as e:
            logger.warning(f"Failed to initialize ViT: {e}")
            logger.warning("Will use heuristic-based classification")
            self.image_classifier = ImageClassifier(config=ViTConfig(device=device))

        # PDF Link Extractor
        self.link_extractor = PDFLinkExtractor()

        logger.info("DSD initialization complete")

    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        min_split_level: int = 3,
        figure_width: int = 600,
        ignore_line_break: bool = True,
    ) -> DSDResult:
        """
        Process a PDF document through the complete DSD pipeline.

        This implements the full Context Engineering 2.0 process:
        - Step 1-2: Physical & Logical Analysis (yomitoku)
        - Step 3: TOC Hierarchy Inference (LayoutLMv3)
        - Step 4: Image Classification (ViT)
        - Step 5: Structural Map Construction
        - Step 6-8: Markdown Generation with Metadata

        Args:
            pdf_path: Path to input PDF file
            output_dir: Path to output directory
            min_split_level: Minimum TOC depth for file splitting
            figure_width: Width in pixels for figure display
            ignore_line_break: If True, remove line breaks within paragraphs

        Returns:
            DSDResult with complete processing results
        """
        pdf_path = Path(pdf_path)
        logger.info(f"[DSD] Processing: {pdf_path.name}")

        # ============================================================
        # PHASE 1: Physical & Logical Analysis (yomitoku)
        # ============================================================
        logger.info("[DSD] Phase 1: Physical & Logical Analysis (yomitoku)...")

        # Load PDF and extract pages
        pdf = pdfium.PdfDocument(str(pdf_path))
        page_images = {}

        # Process all pages
        all_pages_results = []
        for page_num in range(len(pdf)):
            logger.info(f"  Processing page {page_num + 1}/{len(pdf)}...")

            # Render page as image
            page = pdf[page_num]
            bitmap = page.render(scale=2.0)
            img = bitmap.to_numpy()
            page_images[page_num] = img

            # Run yomitoku DocumentAnalyzer
            results, _, _ = self.document_analyzer(img)
            all_pages_results.append(results)

        pdf.close()

        # Aggregate results from all pages
        all_paragraphs = []
        all_tables = []
        all_figures = []
        offset = 0

        for page_num, results in enumerate(all_pages_results):
            # Update orders with page offset
            for p in results.paragraphs:
                p.order += offset
                all_paragraphs.append(p)
            for t in results.tables:
                t.order += offset
                all_tables.append(t)
            for f in results.figures:
                f.order += offset
                all_figures.append(f)

            # Calculate offset for next page
            max_order = max(
                [p.order for p in results.paragraphs]
                + [t.order for t in results.tables]
                + [f.order for f in results.figures]
                + [0]
            )
            offset = max_order + 1

        logger.info(
            f"  Detected: {len(all_paragraphs)} paragraphs, "
            f"{len(all_tables)} tables, {len(all_figures)} figures"
        )

        # ============================================================
        # PHASE 1.5: Link Extraction (Optional)
        # ============================================================
        logger.info("[DSD] Phase 1.5: Extracting hyperlinks from PDF...")

        # Re-open PDF for link extraction
        pdf_for_links = pdfium.PdfDocument(str(pdf_path))
        total_links = 0

        for page_num in range(len(pdf_for_links)):
            page = pdf_for_links[page_num]

            # Extract links from this page
            links = self.link_extractor.extract_links_from_page(page, page_num)
            total_links += len(links)

            # Associate links with paragraphs from this page
            page_paragraphs = [
                p
                for p in all_paragraphs
                if (page_num * 1000) <= p.order < ((page_num + 1) * 1000)
            ]

            self.link_extractor.associate_links_with_paragraphs(links, page_paragraphs)

        pdf_for_links.close()

        logger.info(f"  Extracted {total_links} hyperlinks from PDF")

        # ============================================================
        # PHASE 2: TOC Hierarchy Inference (LayoutLMv3)
        # ============================================================
        logger.info("[DSD] Phase 2: TOC Hierarchy Inference (LayoutLMv3)...")

        # Classify all paragraphs to infer TOC hierarchy
        # Use first page image for visual context
        page_img = page_images.get(0)
        enhanced_paragraphs = self.logical_classifier.classify_batch(
            all_paragraphs, page_img
        )

        # Count headings
        headings = [p for p in enhanced_paragraphs if p.toc_level is not None]
        logger.info(f"  Inferred {len(headings)} TOC headings")

        # ============================================================
        # PHASE 3: Image Classification (ViT)
        # ============================================================
        logger.info("[DSD] Phase 3: Image Classification (ViT)...")

        # Classify all figures
        enhanced_figures = []
        for figure in all_figures:
            # Find the page this figure belongs to
            # Simple heuristic: use first page for now
            # In production, track page numbers properly
            page_img = page_images.get(0)
            enhanced_figure = self.image_classifier.classify(figure, page_img)
            enhanced_figures.append(enhanced_figure)

        # Count by type
        diagrams = [f for f in enhanced_figures if f.semantic_type == "Diagram"]
        textual_images = [
            f for f in enhanced_figures if f.semantic_type == "Textual_Image"
        ]
        logger.info(
            f"  Classified: {len(diagrams)} Diagrams, {len(textual_images)} Textual Images"
        )

        # ============================================================
        # PHASE 4: Structural Map Construction
        # ============================================================
        logger.info("[DSD] Phase 4: Structural Map Construction...")

        builder = StructuralMapBuilder(source_document=pdf_path.name)
        structural_map = builder.build(
            paragraphs=enhanced_paragraphs,
            tables=all_tables,
            figures=enhanced_figures,
        )

        logger.info(f"  Built structural map with {len(structural_map.nodes)} root nodes")

        # ============================================================
        # PHASE 5: Markdown Generation with Metadata
        # ============================================================
        logger.info("[DSD] Phase 5: Markdown Generation...")

        generator = TOCMarkdownGenerator(
            output_dir=output_dir,
            min_split_level=min_split_level,
            figure_width=figure_width,
            ignore_line_break=ignore_line_break,
        )

        # Use first page image for figure extraction
        # In production, maintain proper page-to-figure mapping
        page_images_for_gen = {0: page_images.get(0)}

        generator.generate(structural_map, page_images_for_gen)

        # ============================================================
        # Create DSDResult
        # ============================================================
        result = DSDResult(
            structural_map=structural_map,
            enhanced_paragraphs=enhanced_paragraphs,
            enhanced_figures=enhanced_figures,
            tables=all_tables,
            statistics={
                "total_pages": len(pdf),
                "total_paragraphs": len(all_paragraphs),
                "total_tables": len(all_tables),
                "total_figures": len(all_figures),
                "total_headings": len(headings),
                "total_diagrams": len(diagrams),
                "total_textual_images": len(textual_images),
                "toc_nodes": len(structural_map.nodes),
            },
        )

        # ============================================================
        # Print Summary
        # ============================================================
        logger.info("[DSD] Processing complete!")
        logger.info(f"[DSD] コンテキスト・エントロピー削減完了。")
        logger.info(f"[DSD] 論理ノード（TOC）検出数: {result.statistics['total_headings']}")
        logger.info(f"[DSD] 保持図解（Diagrams）数: {result.statistics['total_diagrams']}")
        logger.info(
            f"[DSD] 置換文章画像（Textual Images）数: {result.statistics['total_textual_images']}"
        )
        logger.info(f"[DSD] 出力ディレクトリ: {output_dir}")

        return result

    def __call__(
        self,
        pdf_path: str,
        output_dir: str,
        min_split_level: int = 3,
        figure_width: int = 600,
        ignore_line_break: bool = True,
    ) -> DSDResult:
        """Convenience method for processing."""
        return self.process_pdf(
            pdf_path, output_dir, min_split_level, figure_width, ignore_line_break
        )
