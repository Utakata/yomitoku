# Document Structure Deconstructor (DSD)

**Context Engineering 2.0 準拠のドキュメント構造化システム**

## 概要

Document Structure Deconstructor (DSD) は、論文 [arXiv:2510.26493v1](https://arxiv.org) で提唱された「Context Engineering 2.0」の理論を実装したシステムです。PDFドキュメント（高エントロピー）を、LLMやRAGシステムが効率的に利用できる構造化データセット（低エントロピー）に変換します。

### コア・コンセプト

DSDは、人間とAIの間に存在する「インテリジェンス・ギャップ」を埋めるために設計されました：

- **人間**：「1.1 節」を見て、自動的に「1章の下位階層」と理解
- **AI**：単なるピクセルとテキストの羅列として認識

DSDは、この暗黙の文脈を明示的な構造へと変換します。

## アーキテクチャ

DSDは3つの専門化されたAIコンポーネントを協調動作させます：

### 1. 👁️ The Eyes: yomitoku
- **役割**：物理レイアウトの検出
- **機能**：OCR、テキスト検出、表構造認識、読み順推定
- **出力**：物理ブロック（テキスト、表、図）の座標とデータ

### 2. 🧠 The Left Brain: LayoutLMv3
- **役割**：論理的階層の推論
- **機能**：見出しのTOCレベル（章、節、小節）を判定
- **入力**：テキスト内容、フォントサイズ（視覚特徴）、座標
- **出力**：`{role: "Chapter_Title", level: 1, title: "第1章 導入"}`

### 3. 🎨 The Right Brain: ViT (Vision Transformer)
- **役割**：図の意味分類
- **機能**：図を「Diagram」（保持）または「Textual_Image」（OCRでテキスト化）に分類
- **入力**：図の画像データ
- **出力**：`{semantic_type: "Diagram"}`

## 処理フロー

```
PDF入力
  ↓
[Phase 1] yomitoku: 物理レイアウト解析
  ↓
[Phase 2] LayoutLMv3: TOC階層推論
  ↓
[Phase 3] ViT: 図の分類
  ↓
[Phase 4] Structural Map構築（永続メモリ）
  ↓
[Phase 5] Markdown生成 + メタデータ付与
  ↓
構造化データセット出力
```

## 使い方

### 基本的な使用方法

```bash
# インストール
pip install -e .

# 基本実行
yomitoku-dsd input.pdf -o output/

# カスタムオプション付き
yomitoku-dsd input.pdf -o output/ \
  --min-split-level 2 \
  --figure-width 800 \
  --device cuda \
  --verbose
```

### Python APIとして使用

```python
from yomitoku.dsd import DSDOrchestrator

# オーケストレーターの初期化
orchestrator = DSDOrchestrator(
    device="cuda",
    visualize=False,
)

# PDF処理
result = orchestrator.process_pdf(
    pdf_path="document.pdf",
    output_dir="output/",
    min_split_level=3,
)

# 結果の確認
print(f"TOC見出し数: {result.statistics['total_headings']}")
print(f"図解数: {result.statistics['total_diagrams']}")
print(f"文章画像数: {result.statistics['total_textual_images']}")
```

## 出力構造

### ディレクトリ構造の例

```
output/
├── 第1章_導入/
│   ├── 1.1_概要.md              # YAML Frontmatter付き
│   ├── 1.2_背景.md
│   └── media/
│       ├── fig-001.png          # Diagram（図解）
│       └── fig-002.png
├── 第2章_方法/
│   ├── 2.1_実験設定.md
│   ├── 2.2_データセット/
│   │   ├── 2.2.1_収集方法.md
│   │   └── 2.2.2_前処理.md
│   └── media/
│       └── fig-003.png
└── structural_map.json          # 永続的な構造マップ
```

### Markdownファイルの例

```markdown
---
title: "1.1 概要"
level: 2
parent: "第1章 導入"
source_document: "document.pdf"
---

## 1.1 概要

本研究では、Context Engineering 2.0の理論に基づき...

<img src="./media/fig-001.png" alt="システムアーキテクチャ" width="600px">

*図1: システムアーキテクチャの全体像*

| 手法 | 精度 | 処理時間 |
|------|------|----------|
| 提案手法 | 95.2% | 120ms |
| ベースライン | 87.3% | 150ms |

```

## コマンドライン オプション

### 必須引数

- `input`: 入力PDFファイルのパス
- `-o, --output`: 出力ディレクトリのパス

### DSDオプション

- `--min-split-level <int>`: 分割する最小TOC深度（デフォルト: 3）
  - レベル3以下の節は個別のMarkdownファイルになります
  - レベル4以上は親ファイルに統合されます

- `--figure-width <int>`: 図の表示幅（ピクセル、デフォルト: 600）

- `--keep-line-breaks`: 段落内の改行を保持（デフォルト: False）

### モデルオプション

- `--device <cuda|cpu>`: 推論デバイス（デフォルト: cuda）

- `--layoutlmv3-model <path>`: ファインチューニング済みLayoutLMv3モデルのパス（オプション）

- `--vit-model <path>`: ファインチューニング済みViTモデルのパス（オプション）

### yomitokuオプション

- `--reading-order <auto|left2right|right2left|top2bottom>`: 読み順戦略（デフォルト: auto）

- `--visualize`: 可視化出力を有効化

- `--include-meta`: ページヘッダー/フッターを含める

### その他

- `--verbose`: 詳細ログ（DEBUG）を有効化

## Context Engineering 2.0 原則の実装

| 原則 | DSDでの実装 |
|------|------------|
| **エントロピー削減** | PDF（高）→ Structural Map（低） |
| **コンテキスト分離** | yomitoku、LayoutLMv3、ViTが独立したコンテキストで動作 |
| **自己ベーキング** | Structural Mapが永続的な知識構造として機能 |
| **プロアクティブ協調** | YAML Frontmatterによる自発的メタデータ付与 |
| **イニシアティブ・エージェント** | ユーザーの潜在的ニーズ（RAG用構造化）を推論 |
| **意味的連続性** | yomitokuの読み順を厳密に保持 |
| **最小十分性** | Textual_Image→テキスト化で冗長な視覚トークンを削減 |

## プロアクティブなメタデータ付与

DSDの重要な特徴は、**ユーザーが明示的に要求していないメタデータを能動的に付与する**点です。

**なぜ？**
- LLMやRAGシステムは、コンテキスト（出典、階層関係）を即座に理解する必要があります
- DSDは、この潜在的ニーズを推論し、YAML Frontmatterとして各Markdownファイルに埋め込みます

これは、Era 1.0の「受動的な変換器」ではなく、Era 2.0の「協調的エージェント」としての振る舞いです。

## エラー処理

DSDは堅牢なフォールバック戦略を持ちます：

### 1. TOC推論の完全失敗
- **状況**：LayoutLMv3が章・節構造を全く検出できない
- **対応**：単一のMarkdownファイルに全コンテンツを出力
- **警告**：Frontmatterに警告メッセージを挿入

### 2. 部分的な失敗
- **状況**：特定の表のMarkdown変換やOCRが失敗
- **対応**：該当ブロックをスキップ、エラーをログに記録、処理を続行

### 3. モデル未利用時
- **状況**：LayoutLMv3やViTのファインチューニング済みモデルがない
- **対応**：ヒューリスティックベースの分類にフォールバック
  - TOC: 正規表現パターンマッチング（「第1章」「1.1」など）
  - 図: yomitokuが検出したテキスト量で判定

## モデルのファインチューニング

### LayoutLMv3（TOC階層推論）

理想的には、日本語文書データセットでファインチューニングします：

**必要なデータ**:
- 多様なPDFドキュメント（学術論文、技術書、報告書）
- 各見出しに対するアノテーション：`{text, level, role}`

**推奨アプローチ**:
```python
from transformers import LayoutLMv3ForSequenceClassification, Trainer

model = LayoutLMv3ForSequenceClassification.from_pretrained(
    "microsoft/layoutlmv3-base",
    num_labels=7,  # 0:Non-heading, 1-4:Level 1-4, 5:Header, 6:Footer
)

# ファインチューニング実行
trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    # ...
)
trainer.train()

# 保存
model.save_pretrained("./layoutlmv3-toc-classifier")
```

### ViT（図の分類）

**必要なデータ**:
- PDF内の図画像
- ラベル：`Diagram`（グラフ、フローチャート）または `Textual_Image`（埋め込み文章）

**推奨アプローチ**:
```python
from transformers import ViTForImageClassification, Trainer

model = ViTForImageClassification.from_pretrained(
    "google/vit-base-patch16-224",
    num_labels=2,  # 0:Diagram, 1:Textual_Image
)

# ファインチューニング実行
trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    # ...
)
trainer.train()

# 保存
model.save_pretrained("./vit-figure-classifier")
```

### カスタムモデルの使用

```bash
yomitoku-dsd input.pdf -o output/ \
  --layoutlmv3-model ./layoutlmv3-toc-classifier \
  --vit-model ./vit-figure-classifier
```

## パフォーマンス

### 推奨環境

- **GPU**: NVIDIA GPU with 8GB+ VRAM (CUDA対応)
- **CPU**: 8+ cores (GPU未使用時)
- **RAM**: 16GB+
- **Python**: 3.10-3.12

### ベンチマーク（参考値）

| PDFサイズ | ページ数 | 処理時間（GPU） | 処理時間（CPU） |
|-----------|---------|----------------|----------------|
| 小（論文） | 10ページ | ~30秒 | ~2分 |
| 中（技術書） | 50ページ | ~2分 | ~10分 |
| 大（教科書） | 200ページ | ~8分 | ~40分 |

## トラブルシューティング

### 1. `ImportError: transformers`

```bash
pip install transformers torch torchvision
```

### 2. CUDA Out of Memory

```bash
# CPUモードで実行
yomitoku-dsd input.pdf -o output/ --device cpu
```

### 3. TOC構造が検出されない

- `--verbose`で詳細ログを確認
- 正規表現パターンが文書の構造に合っているか確認
- カスタムLayoutLMv3モデルのファインチューニングを検討

### 4. 図がすべてDiagramとして保持される

- ViTのファインチューニングモデルを使用
- または、heuristic分類のロジックを調整

## ライセンス

DSDモジュールは yomitoku プロジェクトの一部であり、同じライセンス（CC BY-NC-SA 4.0）が適用されます。

## 引用

DSDを研究で使用する場合は、以下を引用してください：

```bibtex
@article{contextengineering2024,
  title={Context Engineering 2.0: Principles for Intelligent Agent Systems},
  author={...},
  journal={arXiv preprint arXiv:2510.26493},
  year={2024}
}

@software{yomitoku2024,
  title={Yomitoku: AI-Powered Japanese Document Analysis},
  author={Kinoshita, Kotaro},
  year={2024},
  url={https://github.com/kotaro-kinoshita/yomitoku}
}
```

## 貢献

バグ報告、機能リクエスト、プルリクエストを歓迎します！

GitHub Issue: https://github.com/kotaro-kinoshita/yomitoku/issues

## サポート

- **Documentation**: https://kotaro-kinoshita.github.io/yomitoku/
- **GitHub**: https://github.com/kotaro-kinoshita/yomitoku
- **Email**: kotaro.kinoshita@mlism.com

---

**Document Structure Deconstructor (DSD)**
Context Engineering 2.0 Compliant System
Developed as part of the yomitoku project
