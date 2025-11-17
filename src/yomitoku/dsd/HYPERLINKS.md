# ハイパーリンク機能 (Hyperlink Features)

## 概要

DSDは、PDF文書内のハイパーリンク（外部リンクと内部相互参照）を自動抽出し、Markdown形式のリンクとして保持します。

この機能により、生成されるMarkdownデータセットは、元のPDF文書が持っていたナビゲーション機能とリンク情報を維持します。

---

## サポートされるリンクタイプ

### 1. 外部リンク (External Links)
- **説明**: HTTP/HTTPS URLへのリンク
- **ソース**: PDFのリンクアノテーション、埋め込みURL
- **出力**: `[リンクテキスト](https://example.com)`

**例**:
```markdown
詳細については、[公式ドキュメント](https://docs.example.com)を参照してください。
```

### 2. 内部リンク (Internal Links)
- **説明**: 文書内の他のセクションへの相互参照
- **ソース**: PDFの内部リンク、ページ参照、目次リンク
- **解決**: TOC階層とanchor_idを使用して適切なMarkdownファイルパスに変換
- **出力**: `[リンクテキスト](../chapter2/section2-1.md#anchor)`

**例**:
```markdown
この概念については、[第2章 方法](../第2章_方法/2-1_実験設定.md#2-1-実験設定)で詳しく説明します。
```

---

## 実装アーキテクチャ

### コンポーネント

#### 1. **LinkSchema** (`schemas.py`)
リンク情報を保持するデータ構造：
- `link_type`: "external" または "internal"
- `url`: 外部リンクのURL
- `target_page`: 内部リンクのターゲットページ番号
- `target_anchor`: 内部リンクのターゲットanchor ID
- `text`: リンクテキスト
- `bbox`: リンクの位置（バウンディングボックス）

#### 2. **LogicalRoleClassifier** (`logical_role_classifier.py`)
- 見出しから自動的にanchor IDを生成
- 例: "1.1 概要" → "1-1-概要"
- 日本語、英数字、ハイフンを保持し、URLセーフな形式に変換

#### 3. **PDFLinkExtractor** (`pdf_link_extractor.py`)
- PDFページからリンクアノテーションを抽出
- リンクのbboxを使用して、対応する段落に関連付け
- 外部リンクと内部リンクを区別

#### 4. **StructuralMapBuilder** (`structural_map.py`)
- `link_registry`: anchor_id → Markdownファイルパス のマッピングを構築
- 内部リンクの解決基盤を提供

#### 5. **ContentTransformer** (`content_transformer.py`)
- リンクをMarkdown形式に変換
- 外部リンク: `[text](url)`
- 内部リンク: link_registryを使用して相対パスを計算し、`[text](relative_path#anchor)`

#### 6. **TOCMarkdownGenerator** (`markdown_generator.py`)
- 各TOCノードのmarkdown_pathを設定
- link_registryを更新（anchor_id → 実際のファイルパス）
- ContentTransformerにlink_registryと現在のファイルパスを渡す

---

## 処理フロー

```
1. PDFロード
   ↓
2. [PHASE 1] yomitoku: テキスト・レイアウト解析
   ↓
3. [PHASE 1.5] PDFLinkExtractor: リンク抽出
   ・外部URL、内部ページリンクを検出
   ・bboxに基づいて段落に関連付け
   ↓
4. [PHASE 2] LogicalRoleClassifier: TOC階層推論
   ・見出しにanchor_idを自動生成
   ↓
5. [PHASE 4] StructuralMapBuilder: 構造マップ構築
   ・link_registry初期化（anchor_id → ""）
   ↓
6. [PHASE 5] TOCMarkdownGenerator: Markdown生成
   ・各ノードのmarkdown_pathを設定
   ・link_registryを更新（anchor_id → 実際のパス）
   ・ContentTransformerでリンクをMarkdown形式に変換
   ↓
7. Markdown出力
   ・外部リンク: [text](url)
   ・内部リンク: [text](relative_path#anchor)
```

---

## 使用例

### 入力PDF
```
目次:
  第1章 導入 .......... 1
    1.1 概要 .......... 2
  第2章 方法 .......... 5
    2.1 実験設定 ...... 6

本文:
「詳細は1.1節を参照」 ← 内部リンク（ページ2へ）
「公式サイト: https://example.com」 ← 外部リンク
```

### 出力Markdown

**第1章_導入/1.1_概要.md**:
```markdown
---
title: "1.1 概要"
level: 2
parent: "第1章 導入"
source_document: "document.pdf"
---

## 1.1 概要 {#1-1-概要}

本研究では...
```

**第2章_方法/2.1_実験設定.md**:
```markdown
---
title: "2.1 実験設定"
level: 2
parent: "第2章 方法"
source_document: "document.pdf"
---

## 2.1 実験設定 {#2-1-実験設定}

詳細は[1.1節](../第1章_導入/1.1_概要.md#1-1-概要)を参照してください。

公式サイト: [https://example.com](https://example.com)
```

---

## 制限事項

### pypdfium2のAPI制限
- pypdfium2のリンク抽出APIは、バージョンや機能によって制限がある場合があります
- 一部のPDFでは、リンク情報が適切に埋め込まれていない場合があります
- 複雑なリンク構造（名前付きデスティネーション等）は、完全にサポートされない可能性があります

### 内部リンクの解決
- 内部リンクは、anchor_idが正しく生成された見出しにのみ解決されます
- ページ番号のみの参照は、対応する見出しが見つからない場合、解決されない場合があります

### リンクテキストの抽出
- PDFによっては、リンクテキストが明示的に埋め込まれていない場合があります
- その場合、URLまたは「link」というフォールバックテキストが使用されます

---

## 設定オプション

現在、ハイパーリンク機能はデフォルトで有効化されており、特別な設定は不要です。

将来的には、以下のオプションを追加予定：
- `--disable-link-extraction`: リンク抽出を無効化
- `--external-links-only`: 外部リンクのみを抽出
- `--internal-links-only`: 内部リンクのみを抽出

---

## トラブルシューティング

### リンクが抽出されない

**原因**:
- PDFにリンクアノテーションが埋め込まれていない
- pypdfium2のバージョンがリンク抽出をサポートしていない

**対処**:
- 元のPDFを確認し、リンクが実際に機能するか確認
- pypdfium2を最新バージョンにアップデート

### 内部リンクが解決されない

**原因**:
- ターゲット見出しのanchor_idが生成されていない
- LayoutLMv3が見出しを正しく分類していない

**対処**:
- `--verbose`で詳細ログを確認
- TOC階層推論の結果を確認
- 必要に応じて、LayoutLMv3モデルをファインチューニング

### リンクの位置がずれている

**原因**:
- リンクのbboxと段落のbboxの関連付けが正しくない

**対処**:
- PDFの品質を確認（スキャンPDFではなく、テキスト埋め込みPDFを使用）
- yomitokuのレイアウト解析精度を向上（高解像度レンダリング等）

---

## 今後の改善予定

1. **リンク抽出の強化**: より多くのリンクタイプのサポート
2. **名前付きデスティネーション**: PDFの名前付きデスティネーションへの対応
3. **リンクの検証**: 生成されたMarkdownリンクの有効性を検証
4. **統計情報**: 抽出されたリンクの統計情報を出力

---

## 参考

- **schemas.py**: `LinkSchema`, `EnhancedParagraph.links`, `TOCNode.anchor_id`
- **pdf_link_extractor.py**: PDFからのリンク抽出ロジック
- **logical_role_classifier.py**: `_generate_anchor_id()` メソッド
- **content_transformer.py**: `_convert_links_to_markdown()` メソッド
- **structural_map.py**: `_build_link_registry()` メソッド
- **markdown_generator.py**: link_registryの更新とContentTransformerへの渡し

---

**ハイパーリンク機能**
*Context Engineering 2.0: 意味的連続性とプロアクティブ協調の実践*
