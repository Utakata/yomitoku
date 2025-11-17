# 🤖 Document Structure Deconstructor (DSD)

**Context Engineering 2.0に基づいた知的ドキュメント構造化システム**

---

## 📋 概要

**Document Structure Deconstructor (DSD)** は、yomitokuプロジェクトに統合された、革新的なドキュメント構造化システムです。

論文 [arXiv:2510.26493v1](https://arxiv.org) で提唱された **Context Engineering 2.0** の理論を実装し、人間が作成した高エントロピーなPDFドキュメントを、AIシステム（LLM、RAG）が効率的に活用できる低エントロピーな構造化データセットに変換します。

### 🎯 解決する問題

**インテリジェンス・ギャップ**：

- 👤 **人間**：「1.1 節」→ 自動的に「第1章の下位階層」と理解
- 🤖 **AI（LLM）**：単なる文字列として認識、階層関係を理解できない

DSDは、この暗黙の文脈（implicit context）を、明示的な構造（explicit structure）へと変換し、ギャップを埋めます。

---

## ✨ 主な機能

### 1. 🧠 TOC階層の自動推論
- **LayoutLMv3**を使用し、見出しの階層レベル（章、節、小節）を自動判定
- 日本語文書に対応（「第1章」「1.1 概要」「1.1.1 詳細」など）

### 2. 🎨 インテリジェントな図の分類
- **Vision Transformer (ViT)**で図を分類：
  - **Diagram**：グラフ、フローチャート → 画像として保持
  - **Textual_Image**：埋め込み文章 → OCRでテキスト化

### 3. 📁 TOCベースのディレクトリ構造
- 文書の論理階層をそのままディレクトリ構造として再現
- 各節が独立したMarkdownファイルに

### 4. 🏷️ プロアクティブなメタデータ付与
- ユーザーが要求していなくても、各Markdownファイルに**YAML Frontmatter**を自動付与
- LLM/RAGシステムが即座にコンテキスト（出典、階層）を理解可能

### 5. 📊 表の完全対応
- yomitokuの高精度な表構造認識
- Markdownテーブルとして自動変換

---

## 🚀 クイックスタート

### インストール

```bash
# yomitokuリポジトリをクローン
git clone https://github.com/kotaro-kinoshita/yomitoku.git
cd yomitoku

# インストール（uvまたはpip）
uv sync
# または
pip install -e .
```

### 基本的な使用方法

```bash
# PDF → 構造化Markdownデータセット
yomitoku-dsd document.pdf -o output/

# カスタムオプション
yomitoku-dsd document.pdf -o output/ \
  --min-split-level 2 \
  --figure-width 800 \
  --device cuda \
  --verbose
```

### Python APIとして使用

```python
from yomitoku import DSDOrchestrator

# 初期化
orchestrator = DSDOrchestrator(device="cuda")

# PDF処理
result = orchestrator.process_pdf(
    pdf_path="document.pdf",
    output_dir="output/",
    min_split_level=3,
)

# 統計情報
print(f"TOC見出し数: {result.statistics['total_headings']}")
print(f"図解数: {result.statistics['total_diagrams']}")
```

---

## 📂 出力例

### 入力：`論文.pdf`

```
論文.pdf
├── 第1章 導入
│   ├── 1.1 概要
│   └── 1.2 背景
├── 第2章 方法
│   ├── 2.1 実験設定
│   └── 2.2 データセット
└── 第3章 結果
    └── 3.1 評価
```

### 出力：`output/`

```
output/
├── 第1章_導入/
│   ├── 1.1_概要.md              # ⬅️ YAML Frontmatter付き
│   ├── 1.2_背景.md
│   └── media/
│       └── fig-001.png          # ⬅️ Diagram（図解）
├── 第2章_方法/
│   ├── 2.1_実験設定.md
│   ├── 2.2_データセット.md
│   └── media/
│       ├── fig-002.png
│       └── fig-003.png
├── 第3章_結果/
│   └── 3.1_評価.md
└── structural_map.json          # ⬅️ 永続的な構造マップ
```

### Markdownファイルの例：`1.1_概要.md`

```markdown
---
title: "1.1 概要"
level: 2
parent: "第1章 導入"
source_document: "論文.pdf"
---

## 1.1 概要

本研究では、Context Engineering 2.0の理論に基づき、
ドキュメント構造化システムを提案する。

<img src="./media/fig-001.png" alt="システム全体図" width="600px">

*図1: システムアーキテクチャ*

実験結果を表1に示す。

| 手法 | 精度 | 処理時間 |
|------|------|----------|
| 提案手法 | 95.2% | 120ms |
| ベースライン | 87.3% | 150ms |
```

---

## 🏗️ アーキテクチャ

DSDは3つの専門AIコンポーネントを協調動作させます：

```
┌─────────────────────────────────────────┐
│   DSD (Document Structure Deconstructor) │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 1-2: 物理・論理解析 (yomitoku)      │
│  👁️ The Eyes: OCR、レイアウト、表認識   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 3: TOC階層推論 (LayoutLMv3)        │
│  🧠 The Left Brain: 論理的役割の判定    │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 4: 図の分類 (ViT)                  │
│  🎨 The Right Brain: Diagram vs Text    │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 5: Structural Map構築              │
│  🗺️ 永続的なTOCツリー                   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 6-8: Markdown生成 + メタデータ     │
│  📝 ディレクトリ構造 + YAML Frontmatter │
└─────────────────────────────────────────┘
```

---

## 💡 Context Engineering 2.0の実装

| Context Engineering 2.0の原則 | DSDでの実装 |
|-------------------------------|------------|
| **エントロピー削減** | PDF（高エントロピー） → Structural Map（低エントロピー） |
| **コンテキスト分離** | yomitoku、LayoutLMv3、ViTが独立したコンテキストで動作 |
| **自己ベーキング** | Structural Mapが永続的な知識構造として保存 |
| **プロアクティブ協調** | 明示的な要求なしでYAML Frontmatterを付与 |
| **イニシアティブ・エージェント** | ユーザーの潜在的ニーズ（RAG用構造化）を推論 |
| **意味的連続性** | yomitokuの読み順を厳密に保持 |
| **最小十分性** | Textual_Image→テキスト化で冗長な視覚トークンを削減 |

---

## 🛠️ コマンドラインオプション

```bash
yomitoku-dsd [OPTIONS] INPUT -o OUTPUT

必須引数:
  INPUT                     入力PDFファイルのパス
  -o, --output OUTPUT       出力ディレクトリのパス

DSDオプション:
  --min-split-level N       分割する最小TOC深度（デフォルト: 3）
  --figure-width N          図の表示幅（ピクセル、デフォルト: 600）
  --keep-line-breaks        段落内の改行を保持

モデルオプション:
  --device {cuda,cpu}       推論デバイス（デフォルト: cuda）
  --layoutlmv3-model PATH   ファインチューニング済みLayoutLMv3モデル
  --vit-model PATH          ファインチューニング済みViTモデル

yomitokuオプション:
  --reading-order {auto,left2right,right2left,top2bottom}
                            読み順戦略（デフォルト: auto）
  --visualize               可視化出力を有効化
  --include-meta            ページヘッダー/フッターを含める

その他:
  --verbose                 詳細ログ（DEBUG）を有効化
```

---

## 📚 ドキュメント

詳細なドキュメントは以下を参照：

- **DSDモジュールREADME**: [`src/yomitoku/dsd/README.md`](src/yomitoku/dsd/README.md)
- **アーキテクチャ設計**: [`DSD_ARCHITECTURE.md`](DSD_ARCHITECTURE.md)
- **デモスクリプト**: [`demo/simple_dsd.py`](demo/simple_dsd.py)

---

## 🔬 モデルのファインチューニング

DSDは、ファインチューニング済みモデルなしでも動作しますが（ヒューリスティックフォールバック）、
最高の精度を得るには、日本語文書データセットでのファインチューニングを推奨します。

### LayoutLMv3（TOC階層推論）

```python
from transformers import LayoutLMv3ForSequenceClassification

model = LayoutLMv3ForSequenceClassification.from_pretrained(
    "microsoft/layoutlmv3-base",
    num_labels=7,  # 0:Non-heading, 1-4:Level 1-4, 5:Header, 6:Footer
)
# ファインチューニング実行...
model.save_pretrained("./layoutlmv3-toc-classifier")
```

### ViT（図の分類）

```python
from transformers import ViTForImageClassification

model = ViTForImageClassification.from_pretrained(
    "google/vit-base-patch16-224",
    num_labels=2,  # 0:Diagram, 1:Textual_Image
)
# ファインチューニング実行...
model.save_pretrained("./vit-figure-classifier")
```

使用：
```bash
yomitoku-dsd document.pdf -o output/ \
  --layoutlmv3-model ./layoutlmv3-toc-classifier \
  --vit-model ./vit-figure-classifier
```

---

## 🚨 エラー処理

DSDは堅牢なフォールバック戦略を持ちます：

1. **TOC推論の完全失敗** → 単一Markdownファイルに全コンテンツを出力（警告付き）
2. **部分的な失敗** → 該当ブロックをスキップ、処理を続行
3. **モデル未利用** → ヒューリスティック分類にフォールバック

---

## 📊 パフォーマンス

| PDFサイズ | ページ数 | 処理時間（GPU） | 処理時間（CPU） |
|-----------|---------|----------------|----------------|
| 小（論文） | 10ページ | ~30秒 | ~2分 |
| 中（技術書） | 50ページ | ~2分 | ~10分 |
| 大（教科書） | 200ページ | ~8分 | ~40分 |

**推奨環境**:
- GPU: NVIDIA GPU with 8GB+ VRAM
- RAM: 16GB+
- Python: 3.10-3.12

---

## 🤝 貢献

バグ報告、機能リクエスト、プルリクエストを歓迎します！

**GitHub**: https://github.com/kotaro-kinoshita/yomitoku

---

## 📖 引用

DSDを研究で使用する場合は、以下を引用してください：

```bibtex
@article{contextengineering2024,
  title={Context Engineering 2.0: Principles for Intelligent Agent Systems},
  author={...},
  journal={arXiv preprint arXiv:2510.26493},
  year={2024}
}

@software{yomitoku2024,
  title={Yomitoku: AI-Powered Japanese Document Analysis with DSD},
  author={Kinoshita, Kotaro},
  year={2024},
  url={https://github.com/kotaro-kinoshita/yomitoku}
}
```

---

## 📧 サポート

- **Documentation**: https://kotaro-kinoshita.github.io/yomitoku/
- **GitHub Issues**: https://github.com/kotaro-kinoshita/yomitoku/issues
- **Email**: kotaro.kinoshita@mlism.com

---

## 📜 ライセンス

DSDモジュールは yomitoku プロジェクトの一部であり、同じライセンス（**CC BY-NC-SA 4.0**）が適用されます。

---

**🤖 Document Structure Deconstructor (DSD)**
*Context Engineering 2.0 Compliant System*
*Developed as part of the yomitoku project*

---
