"""
TOC-based Markdown Generator - generates structured Markdown files from Structural Map.

This implements Steps 6-8 of the DSD process: directory generation, file splitting,
and proactive metadata injection.
"""

import os
import json
import logging
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

from yomitoku.utils.misc import save_image
from .schemas import StructuralMap, TOCNode, EnhancedFigure
from .content_transformer import ContentTransformer

logger = logging.getLogger(__name__)


class TOCMarkdownGenerator:
    """
    Generates TOC-based directory structure with Markdown files and metadata.

    This is the final step of DSD, implementing Context-Cooperative behavior
    through proactive metadata injection.
    """

    def __init__(
        self,
        output_dir: str,
        min_split_level: int = 3,
        figure_width: int = 600,
        ignore_line_break: bool = True,
    ):
        """
        Initialize the Markdown generator.

        Args:
            output_dir: Output directory for generated files
            min_split_level: Minimum TOC depth for file splitting (default: 3)
            figure_width: Width in pixels for figure display
            ignore_line_break: If True, remove line breaks within paragraphs
        """
        self.output_dir = Path(output_dir)
        self.min_split_level = min_split_level
        self.figure_width = figure_width
        self.ignore_line_break = ignore_line_break
        self.media_dir = self.output_dir / "media"
        self.figure_counter = 0
        self.page_images = {}  # Store page images for figure extraction
        self.link_registry = {}  # Will be set from structural_map
        self.transformer = None  # Will be created with link_registry

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename.

        Args:
            name: Original name

        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Limit length
        if len(name) > 100:
            name = name[:100]
        return name

    def _create_yaml_frontmatter(
        self,
        title: str,
        level: int,
        parent_title: Optional[str],
        source_document: str,
    ) -> str:
        """
        Create YAML frontmatter for proactive metadata injection.

        This is the core of Context-Cooperative behavior: anticipating
        downstream LLM/RAG needs without explicit user request.

        Args:
            title: Node title
            level: TOC hierarchy level
            parent_title: Parent node title (if any)
            source_document: Original PDF filename

        Returns:
            YAML frontmatter string
        """
        frontmatter = "---\n"
        frontmatter += f'title: "{title}"\n'
        frontmatter += f"level: {level}\n"
        if parent_title:
            frontmatter += f'parent: "{parent_title}"\n'
        frontmatter += f'source_document: "{source_document}"\n'
        frontmatter += "---\n\n"
        return frontmatter

    def _save_figure(
        self,
        figure: EnhancedFigure,
        page_img: np.ndarray,
    ) -> str:
        """
        Save a Diagram figure to media directory.

        Args:
            figure: EnhancedFigure classified as Diagram
            page_img: Full page image

        Returns:
            Relative path to saved figure
        """
        # Create media directory if it doesn't exist
        self.media_dir.mkdir(parents=True, exist_ok=True)

        # Extract figure region
        x1, y1, x2, y2 = map(int, figure.box)
        figure_img = page_img[y1:y2, x1:x2, :]

        # Generate filename
        self.figure_counter += 1
        figure_filename = f"fig-{self.figure_counter:03d}.png"
        figure_path = self.media_dir / figure_filename

        # Save image
        try:
            save_image(figure_img, str(figure_path))
            logger.debug(f"Saved figure to: {figure_path}")
        except Exception as e:
            logger.error(f"Failed to save figure: {e}")
            return ""

        # Return relative path from output_dir
        return f"./media/{figure_filename}"

    def _generate_node_content(
        self,
        node: TOCNode,
        structural_map: StructuralMap,
        page_images: Dict[int, np.ndarray],
    ) -> str:
        """
        Generate Markdown content for a single TOC node.

        Args:
            node: TOC node to generate content for
            structural_map: Complete structural map
            page_images: Dictionary mapping page numbers to images

        Returns:
            Markdown content string
        """
        content = []

        # Add node title as header
        header_level = min(node.level, 6)
        content.append(f"{'#' * header_level} {node.title}\n\n")

        # Process content blocks in order
        content_blocks = []
        for block_id in node.content_blocks:
            if block_id in structural_map.content_registry:
                content_blocks.append(structural_map.content_registry[block_id])

        # Sort by order
        content_blocks.sort(key=lambda b: b.get("order", 0))

        # Transform each content block
        for block in content_blocks:
            content_type = block["type"]
            content_obj = block["content"]

            # Handle figures specially - need to save Diagrams
            if content_type == "figure":
                figure = content_obj
                if figure.semantic_type == "Diagram":
                    # Find the page image for this figure
                    # This is a simplification - in production, track page numbers properly
                    page_img = page_images.get(0)  # Default to first page for now
                    if page_img is not None:
                        figure_path = self._save_figure(figure, page_img)
                        if figure_path:
                            md_text = self.transformer(content_type, content_obj, figure_path)
                            content.append(md_text)
                    else:
                        logger.warning(f"No page image available for figure at order {figure.order}")
                else:
                    # Textual_Image - convert to text
                    md_text = self.transformer(content_type, content_obj)
                    content.append(md_text)
            else:
                # Paragraph or table
                md_text = self.transformer(content_type, content_obj)
                content.append(md_text)

        return "".join(content)

    def _generate_node_markdown(
        self,
        node: TOCNode,
        structural_map: StructuralMap,
        page_images: Dict[int, np.ndarray],
        parent_dir: Path,
    ) -> None:
        """
        Generate Markdown file(s) for a TOC node and its children.

        Args:
            node: TOC node to process
            structural_map: Complete structural map
            page_images: Dictionary of page images
            parent_dir: Parent directory for output
        """
        # Determine if this node should be split into its own file
        should_split = node.level <= self.min_split_level

        if should_split:
            # Create directory for this node if it has children
            if node.children:
                node_dir_name = self._sanitize_filename(node.title)
                node_dir = parent_dir / node_dir_name
                node_dir.mkdir(parents=True, exist_ok=True)
            else:
                node_dir = parent_dir

            # Create Markdown file for this node
            filename = self._sanitize_filename(node.title) + ".md"
            filepath = parent_dir / filename

            # Update node's markdown_path and link_registry
            relative_path = filepath.relative_to(self.output_dir)
            node.markdown_path = str(relative_path)

            # Update link_registry if node has anchor_id
            if node.anchor_id:
                self.link_registry[node.anchor_id] = str(relative_path)

            # Create ContentTransformer with link_registry and current path
            self.transformer = ContentTransformer(
                ignore_line_break=self.ignore_line_break,
                link_registry=self.link_registry,
                current_markdown_path=str(relative_path),
            )

            # Generate content
            content = []

            # Add YAML frontmatter (proactive metadata injection)
            frontmatter = self._create_yaml_frontmatter(
                title=node.title,
                level=node.level,
                parent_title=node.parent_title,
                source_document=structural_map.source_document,
            )
            content.append(frontmatter)

            # Add node content
            node_content = self._generate_node_content(node, structural_map, page_images)
            content.append(node_content)

            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("".join(content))

            logger.info(f"Generated: {filepath}")

            # Process children
            if node.children:
                for child in node.children:
                    self._generate_node_markdown(
                        child,
                        structural_map,
                        page_images,
                        node_dir,
                    )
        else:
            # Don't split - include this node and children in parent file
            # This is handled by the parent node's content generation
            pass

    def generate(
        self,
        structural_map: StructuralMap,
        page_images: Optional[Dict[int, np.ndarray]] = None,
    ) -> str:
        """
        Generate complete directory structure with Markdown files.

        Args:
            structural_map: Complete structural map from StructuralMapBuilder
            page_images: Dictionary mapping page numbers to images (for figure extraction)

        Returns:
            Path to output directory
        """
        if page_images is None:
            page_images = {}

        logger.info(f"Generating Markdown files in: {self.output_dir}")

        # Initialize link_registry from structural_map
        self.link_registry = structural_map.link_registry.copy()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check if structural map has nodes
        if not structural_map.nodes:
            logger.warning("Structural map has no nodes - generating single file")
            # Fallback: create single file with all content
            self._generate_fallback_markdown(structural_map, page_images)
            return str(self.output_dir)

        # Generate Markdown files for each root node
        for node in structural_map.nodes:
            self._generate_node_markdown(
                node,
                structural_map,
                page_images,
                self.output_dir,
            )

        # Save structural map as JSON for reference
        self._save_structural_map_json(structural_map)

        logger.info("Markdown generation complete")
        return str(self.output_dir)

    def _generate_fallback_markdown(
        self,
        structural_map: StructuralMap,
        page_images: Dict[int, np.ndarray],
    ) -> None:
        """
        Generate a single Markdown file when TOC structure is unavailable.

        This is the fallback strategy for catastrophic failure.

        Args:
            structural_map: Structural map (may have empty nodes)
            page_images: Page images for figure extraction
        """
        logger.warning("Using fallback: generating single Markdown file")

        filename = self._sanitize_filename(structural_map.title) + ".md"
        filepath = self.output_dir / filename

        content = []

        # Add frontmatter with warning
        frontmatter = "---\n"
        frontmatter += f'title: "{structural_map.title}"\n'
        frontmatter += f'source_document: "{structural_map.source_document}"\n'
        frontmatter += "warning: \"TOC structure could not be inferred. All content in single file.\"\n"
        frontmatter += "---\n\n"
        content.append(frontmatter)

        # Add title
        content.append(f"# {structural_map.title}\n\n")

        # Collect all content blocks
        all_blocks = []
        for block_id, block_data in structural_map.content_registry.items():
            all_blocks.append(block_data)

        # Sort by order
        all_blocks.sort(key=lambda b: b.get("order", 0))

        # Transform each block
        for block in all_blocks:
            content_type = block["type"]
            content_obj = block["content"]

            if content_type == "figure":
                figure = content_obj
                if figure.semantic_type == "Diagram":
                    page_img = page_images.get(0)
                    if page_img is not None:
                        figure_path = self._save_figure(figure, page_img)
                        if figure_path:
                            md_text = self.transformer(content_type, content_obj, figure_path)
                            content.append(md_text)
                else:
                    md_text = self.transformer(content_type, content_obj)
                    content.append(md_text)
            else:
                md_text = self.transformer(content_type, content_obj)
                content.append(md_text)

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("".join(content))

        logger.info(f"Generated fallback file: {filepath}")

    def _save_structural_map_json(self, structural_map: StructuralMap) -> None:
        """
        Save structural map as JSON for reference and future use.

        Args:
            structural_map: Structural map to save
        """
        json_path = self.output_dir / "structural_map.json"

        try:
            # Convert to dict (Pydantic model)
            map_dict = structural_map.model_dump()

            # Remove large content objects from content_registry
            # Keep only metadata
            simplified_registry = {}
            for block_id, block_data in map_dict["content_registry"].items():
                simplified_registry[block_id] = {
                    "type": block_data["type"],
                    "order": block_data.get("order", 0),
                }
            map_dict["content_registry"] = simplified_registry

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(map_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved structural map: {json_path}")

        except Exception as e:
            logger.error(f"Failed to save structural map JSON: {e}")

    def __call__(
        self,
        structural_map: StructuralMap,
        page_images: Optional[Dict[int, np.ndarray]] = None,
    ) -> str:
        """Convenience method for generation."""
        return self.generate(structural_map, page_images)
