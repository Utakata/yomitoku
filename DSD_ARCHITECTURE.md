# Document Structure Deconstructor (DSD) - Architecture Design

## Overview
DSD extends yomitoku to transform PDF documents from high-entropy monolithic files into low-entropy structured datasets with TOC-based hierarchical organization, following Context Engineering 2.0 principles.

## Architecture

### 1. Component Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Structure Deconstructor              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1-2: Physical & Logical Analysis (Extended yomitoku)      │
├─────────────────────────────────────────────────────────────────┤
│  • TextDetector (DBNetV2) ───┐                                  │
│  • LayoutAnalyzer (RTDETRv2) ─┼──► DocumentAnalyzer             │
│  • TextRecognizer (PARSeq) ───┘                                 │
│  • Reading Order Estimation                                      │
│                                                                  │
│  Output: paragraphs (with role), tables, figures, words         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: TOC Hierarchy Inference (NEW: LayoutLMv3)              │
├─────────────────────────────────────────────────────────────────┤
│  LogicalRoleClassifier:                                          │
│  • Input: paragraphs with role="section_headings"               │
│  • Features: text content, font size, position, visual tokens   │
│  • Output: {"role": "Chapter_Title", "level": 1, ...}          │
│            {"role": "Section_Title", "level": 2, ...}           │
│                                                                  │
│  Model: microsoft/layoutlmv3-base (fine-tuned)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Image Classification (NEW: ViT)                        │
├─────────────────────────────────────────────────────────────────┤
│  ImageClassifier:                                                │
│  • Input: figures (FigureSchema)                                │
│  • Output: {"semantic_type": "Diagram"} or                      │
│            {"semantic_type": "Textual_Image"}                   │
│                                                                  │
│  Model: google/vit-base-patch16-224 (fine-tuned)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Structural Map Construction (NEW)                      │
├─────────────────────────────────────────────────────────────────┤
│  StructuralMapBuilder:                                           │
│  • Build TOC tree from hierarchical paragraphs                  │
│  • Associate content blocks to TOC nodes                        │
│  • Maintain reading order fidelity                              │
│                                                                  │
│  Output: JSON Structural_Map with nested nodes                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6-8: Markdown Generation with Metadata (NEW)              │
├─────────────────────────────────────────────────────────────────┤
│  TOCMarkdownGenerator:                                           │
│  • Generate directory structure from TOC hierarchy              │
│  • Split markdown files by min_split_level                      │
│  • Add YAML Frontmatter (proactive metadata injection)          │
│  • Handle media: Diagram → media/, Textual_Image → OCR text    │
│                                                                  │
│  Output: ZIP archive with directory structure                   │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/yomitoku/dsd/
├── __init__.py
├── logical_role_classifier.py    # LayoutLMv3 integration for TOC hierarchy
├── image_classifier.py            # ViT integration for Diagram vs Textual_Image
├── structural_map.py              # Structural_Map builder (TOC tree)
├── content_transformer.py         # Content transformation (OCR, table conversion)
├── markdown_generator.py          # TOC-based Markdown generation
├── cli.py                         # DSD CLI interface
└── schemas.py                     # DSD-specific schemas

src/yomitoku/dsd/models/
├── __init__.py
├── cfg_layoutlmv3.py              # LayoutLMv3 config
└── cfg_vit.py                     # ViT config
```

## Data Flow

### Phase 1: Analysis (yomitoku + DSD extensions)
```
PDF
 ↓ [yomitoku]
DocumentAnalyzerSchema {
  paragraphs: [
    {box, contents, direction, order, role: "section_headings"},
    {box, contents, direction, order, role: null},
    ...
  ],
  tables: [...],
  figures: [...],
  words: [...]
}
 ↓ [LogicalRoleClassifier]
Enhanced Paragraphs {
  paragraphs: [
    {box, contents, order, role: "section_headings", toc_level: 1, toc_title: "第1章 導入"},
    {box, contents, order, role: "section_headings", toc_level: 2, toc_title: "1.1 概要"},
    {box, contents, order, role: null, toc_level: null},
    ...
  ]
}
 ↓ [ImageClassifier]
Enhanced Figures {
  figures: [
    {box, order, paragraphs, semantic_type: "Diagram"},
    {box, order, paragraphs, semantic_type: "Textual_Image"},
    ...
  ]
}
```

### Phase 2: Structural Map Construction
```
Enhanced Data
 ↓ [StructuralMapBuilder]
Structural_Map (JSON) {
  "title": "Document Title",
  "nodes": [
    {
      "level": 1,
      "title": "第1章 導入",
      "content_blocks": ["block_id_001", "block_id_002"],
      "children": [
        {
          "level": 2,
          "title": "1.1 概要",
          "content_blocks": ["block_id_003", "block_id_004"],
          "children": []
        }
      ]
    }
  ]
}
```

### Phase 3: Markdown Generation
```
Structural_Map
 ↓ [TOCMarkdownGenerator]
Output Directory Structure:
output/
├── 第1章_導入/
│   ├── 1.1_概要.md (with YAML Frontmatter)
│   ├── 1.2_背景.md
│   └── media/
│       ├── fig-001.png
│       └── fig-002.png
├── 第2章_方法/
│   ├── 2.1_実験設定.md
│   └── media/
│       └── fig-003.png
└── structural_map.json
```

## Key Design Decisions

### 1. LayoutLMv3 Integration
- **Purpose**: Infer TOC hierarchy levels from section headings
- **Input**: Paragraphs with `role="section_headings"` from yomitoku
- **Features**: Text content (e.g., "1.1 概要"), bounding box, font size estimation from visual tokens
- **Output**: `toc_level` (1, 2, 3...) and `toc_title`
- **Training**: Fine-tune on Japanese document datasets with TOC annotations

### 2. ViT Integration
- **Purpose**: Classify figures as "Diagram" or "Textual_Image"
- **Input**: Figure images cropped from FigureSchema
- **Output**: `semantic_type`
- **Action**:
  - Diagram → save to media/ folder, insert as `![Figure](./media/fig-001.png)`
  - Textual_Image → run yomitoku OCR, insert as plain text
- **Training**: Fine-tune on dataset of document images with Diagram/Textual_Image labels

### 3. Structural Map as Persistent Memory
- The Structural_Map is the "self-baked" context (Context Engineering 2.0)
- It's a permanent, low-entropy representation of document structure
- Enables TOC-based splitting, metadata injection, and future reuse

### 4. Proactive Metadata Injection
- YAML Frontmatter added to every Markdown file:
  ```yaml
  ---
  title: "1.1 概要"
  level: 2
  parent: "第1章 導入"
  source_document: "original.pdf"
  ---
  ```
- This is "Context-Cooperative" behavior: anticipating LLM/RAG needs without explicit user request

### 5. Error Handling
- **Catastrophic Failure**: If TOC inference fails entirely → fallback to single Markdown file
- **Partial Failure**: If specific table/OCR fails → skip block, log error, continue processing

## CLI Interface

```bash
# Basic usage
yomitoku-dsd input.pdf -o output/

# With options
yomitoku-dsd input.pdf -o output/ \
  --min-split-level 3 \
  --force-ocr \
  --device cuda \
  --visualize

# Options:
#   --min-split-level: Minimum TOC depth for splitting (default: 3)
#   --force-ocr: Force OCR even if PDF has embedded text
#   --device: cuda or cpu
#   --visualize: Generate visualization images
#   --output-format: zip or directory
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create `src/yomitoku/dsd/` module structure
2. Define DSD-specific schemas (TOC node, enhanced paragraph/figure)
3. Implement StructuralMapBuilder (without ML models initially)

### Phase 2: ML Model Integration
4. Integrate LayoutLMv3 for TOC hierarchy inference
5. Integrate ViT for image classification
6. Fine-tune models on sample datasets

### Phase 3: Content Generation
7. Implement ContentTransformer (OCR substitution, table conversion)
8. Implement TOCMarkdownGenerator (directory creation, file splitting, metadata injection)
9. Implement error handling and fallback strategies

### Phase 4: CLI & Testing
10. Implement CLI interface
11. Test with various PDF documents
12. Optimize performance and add progress reporting

## Context Engineering 2.0 Compliance

| Principle | Implementation |
|-----------|----------------|
| **Entropy Reduction** | PDF (high entropy) → Structural_Map (low entropy) |
| **Context Isolation** | Each component (yomitoku, LayoutLMv3, ViT) has isolated context |
| **Self-Baking** | Structural_Map is permanent, reusable memory |
| **Proactive Cooperation** | Metadata injection anticipates LLM/RAG needs |
| **Initiative Agent** | Infers user intent (structured output for RAG) without explicit instruction |
| **Semantic Continuity** | Reading order preservation ensures meaning continuity |
| **Minimal Sufficiency** | Textual_Image → text (removes redundant visual tokens) |

## Success Metrics

1. **Structure Fidelity**: 95%+ accuracy in TOC hierarchy inference
2. **Content Completeness**: 100% of content mapped to correct TOC nodes
3. **Reading Order Preservation**: 100% fidelity to yomitoku's reading order
4. **Image Classification Accuracy**: 90%+ Diagram vs Textual_Image
5. **Metadata Quality**: 100% of Markdown files have valid YAML Frontmatter
6. **Error Resilience**: System continues with partial failures, produces useful output
