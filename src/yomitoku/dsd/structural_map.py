"""
Structural Map Builder - constructs the TOC hierarchy tree.

This is the "self-baking" process that transforms high-entropy content
into a low-entropy, persistent memory structure.
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

from yomitoku.schemas import TableStructureRecognizerSchema
from .schemas import (
    TOCNode,
    StructuralMap,
    EnhancedParagraph,
    EnhancedFigure,
)

logger = logging.getLogger(__name__)


class StructuralMapBuilder:
    """
    Builds the Structural Map - a hierarchical TOC tree with all content mapped.

    This implements the "self-baking" process from Context Engineering 2.0,
    creating a permanent, low-entropy knowledge structure.
    """

    def __init__(self, source_document: str):
        """
        Initialize the builder.

        Args:
            source_document: Original PDF filename
        """
        self.source_document = source_document
        self.content_registry: Dict[str, Dict[str, Any]] = {}
        self.block_id_counter = 0

    def _generate_block_id(self, prefix: str = "block") -> str:
        """Generate a unique block ID."""
        self.block_id_counter += 1
        return f"{prefix}_{self.block_id_counter:06d}"

    def _register_content(
        self, content_type: str, content: Any
    ) -> str:
        """
        Register a content block and return its ID.

        Args:
            content_type: Type of content ('paragraph', 'table', 'figure')
            content: The actual content object

        Returns:
            Block ID
        """
        block_id = self._generate_block_id(content_type[:3])
        self.content_registry[block_id] = {
            "type": content_type,
            "content": content,
            "order": getattr(content, "order", 0),
        }
        return block_id

    def _build_toc_tree(
        self,
        headings: List[EnhancedParagraph],
    ) -> List[TOCNode]:
        """
        Build the TOC tree from heading paragraphs.

        Args:
            headings: List of EnhancedParagraphs with toc_level set

        Returns:
            List of root TOC nodes
        """
        if not headings:
            logger.warning("No headings found to build TOC tree")
            return []

        root_nodes = []
        node_stack = []  # Stack to track current path in tree

        for heading in headings:
            level = heading.toc_level
            title = heading.toc_title or heading.contents
            order = heading.order

            # Register the heading content
            block_id = self._register_content("paragraph", heading)

            # Get anchor_id from heading (set by LogicalRoleClassifier)
            anchor_id = getattr(heading, "anchor_id", None)

            # Create new node
            node = TOCNode(
                level=level,
                title=title,
                content_blocks=[block_id],
                children=[],
                parent_title=None,
                order=order,
                anchor_id=anchor_id,
                markdown_path=None,  # Will be set during Markdown generation
            )

            # Find the correct parent
            # Pop stack until we find a level lower than current
            while node_stack and node_stack[-1]["level"] >= level:
                node_stack.pop()

            if not node_stack:
                # This is a root node
                root_nodes.append(node)
                node_stack.append({"level": level, "node": node})
            else:
                # Add as child to the last node in stack
                parent = node_stack[-1]["node"]
                node.parent_title = parent.title
                parent.children.append(node)
                node_stack.append({"level": level, "node": node})

        return root_nodes

    def _assign_content_to_nodes(
        self,
        nodes: List[TOCNode],
        all_content: List[Any],
    ) -> None:
        """
        Assign content blocks (paragraphs, tables, figures) to TOC nodes.

        Content is assigned to the most recent heading node based on reading order.

        Args:
            nodes: List of TOC nodes (modified in place)
            all_content: List of all content items (paragraphs, tables, figures)
        """

        def flatten_nodes(nodes: List[TOCNode]) -> List[TOCNode]:
            """Flatten the tree into a list ordered by document order."""
            result = []
            for node in nodes:
                result.append(node)
                if node.children:
                    result.extend(flatten_nodes(node.children))
            return result

        flat_nodes = flatten_nodes(nodes)
        if not flat_nodes:
            logger.warning("No TOC nodes to assign content to")
            return

        # Sort nodes by order
        flat_nodes.sort(key=lambda n: n.order)

        # Sort content by order
        sorted_content = sorted(all_content, key=lambda c: getattr(c, "order", 0))

        # Assign content to nodes
        current_node_idx = 0
        current_node = flat_nodes[current_node_idx]

        for content in sorted_content:
            content_order = getattr(content, "order", 0)

            # Skip if content is already registered as a heading
            # (check if content is in any node's first block)
            is_heading = any(
                content.order == node.order for node in flat_nodes
                if hasattr(content, "order") and hasattr(node, "order")
            )
            if is_heading and isinstance(content, EnhancedParagraph) and content.toc_level is not None:
                continue

            # Find the appropriate node for this content
            # The content belongs to the last node whose order <= content order
            while (
                current_node_idx < len(flat_nodes) - 1
                and flat_nodes[current_node_idx + 1].order <= content_order
            ):
                current_node_idx += 1
                current_node = flat_nodes[current_node_idx]

            # Register and add content to current node
            content_type = (
                "paragraph"
                if isinstance(content, EnhancedParagraph)
                else "table"
                if isinstance(content, TableStructureRecognizerSchema)
                else "figure"
            )
            block_id = self._register_content(content_type, content)
            current_node.content_blocks.append(block_id)

            logger.debug(
                f"Assigned {content_type} (order={content_order}) to node '{current_node.title}' (order={current_node.order})"
            )

    def build(
        self,
        paragraphs: List[EnhancedParagraph],
        tables: List[TableStructureRecognizerSchema],
        figures: List[EnhancedFigure],
        document_title: Optional[str] = None,
    ) -> StructuralMap:
        """
        Build the complete Structural Map.

        Args:
            paragraphs: All paragraphs (including headings)
            tables: All tables
            figures: All figures
            document_title: Optional document title (extracted from first heading or filename)

        Returns:
            Complete StructuralMap
        """
        logger.info("Building Structural Map...")

        # Separate headings from regular paragraphs
        headings = [p for p in paragraphs if p.toc_level is not None]
        regular_paragraphs = [p for p in paragraphs if p.toc_level is None]

        logger.info(f"Found {len(headings)} headings, {len(regular_paragraphs)} paragraphs")
        logger.info(f"Found {len(tables)} tables, {len(figures)} figures")

        # Build TOC tree from headings
        toc_nodes = self._build_toc_tree(headings)

        if not toc_nodes:
            logger.warning("Failed to build TOC tree - no headings found")
            # Create a single root node for all content
            all_content = regular_paragraphs + tables + figures
            root_node = TOCNode(
                level=0,
                title=document_title or "Document",
                content_blocks=[],
                children=[],
                parent_title=None,
                order=0,
            )
            # Register all content
            for content in sorted(all_content, key=lambda c: getattr(c, "order", 0)):
                content_type = (
                    "paragraph"
                    if isinstance(content, EnhancedParagraph)
                    else "table"
                    if isinstance(content, TableStructureRecognizerSchema)
                    else "figure"
                )
                block_id = self._register_content(content_type, content)
                root_node.content_blocks.append(block_id)
            toc_nodes = [root_node]
        else:
            # Assign all content to TOC nodes
            all_content = regular_paragraphs + tables + figures
            self._assign_content_to_nodes(toc_nodes, all_content)

        # Determine document title
        if not document_title:
            if toc_nodes:
                document_title = toc_nodes[0].title
            else:
                document_title = self.source_document

        # Build link registry for internal link resolution
        link_registry = self._build_link_registry(toc_nodes, all_paragraphs)

        # Create structural map
        structural_map = StructuralMap(
            title=document_title,
            source_document=self.source_document,
            nodes=toc_nodes,
            content_registry=self.content_registry,
            link_registry=link_registry,
            metadata={
                "total_headings": len(headings),
                "total_paragraphs": len(regular_paragraphs),
                "total_tables": len(tables),
                "total_figures": len(figures),
                "total_toc_nodes": len(toc_nodes),
            },
        )

        logger.info("Structural Map built successfully")
        logger.info(f"  Root nodes: {len(toc_nodes)}")
        logger.info(f"  Total content blocks: {len(self.content_registry)}")
        logger.info(f"  Link registry entries: {len(link_registry)}")

        return structural_map

    def _build_link_registry(
        self,
        toc_nodes: List[TOCNode],
        all_paragraphs: List[EnhancedParagraph],
    ) -> Dict[str, str]:
        """
        Build a link registry for internal link resolution.

        Maps anchor_id → (to be filled with markdown_path during generation).
        This will be completed by the Markdown generator.

        Args:
            toc_nodes: All TOC nodes
            all_paragraphs: All paragraphs (for extracting anchor IDs)

        Returns:
            Dictionary mapping anchor_id to placeholder (to be updated)
        """
        link_registry = {}

        def collect_anchors(nodes: List[TOCNode]):
            for node in nodes:
                if node.anchor_id:
                    # Placeholder - will be updated with actual markdown path
                    link_registry[node.anchor_id] = ""
                if node.children:
                    collect_anchors(node.children)

        collect_anchors(toc_nodes)

        # Also register paragraph anchor IDs
        for para in all_paragraphs:
            if hasattr(para, "anchor_id") and para.anchor_id:
                link_registry[para.anchor_id] = ""

        return link_registry

    def __call__(
        self,
        paragraphs: List[EnhancedParagraph],
        tables: List[TableStructureRecognizerSchema],
        figures: List[EnhancedFigure],
        document_title: Optional[str] = None,
    ) -> StructuralMap:
        """Convenience method for building."""
        return self.build(paragraphs, tables, figures, document_title)
