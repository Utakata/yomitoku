import cv2

from yomitoku import LayoutAnalyzer
from yomitoku.data.functions import load_pdf
from yomitoku.export import save_json

if __name__ == "__main__":
    analyzer = LayoutAnalyzer(visualize=True, device="cuda")
    # PDFファイルを読み込み
    imgs = load_pdf("demo/sample.pdf")
    for i, img in enumerate(imgs):
        results, layout_vis = analyzer(img)

        # JSON形式で解析結果をエクスポート
        save_json(results, f"output_{i}.json", encoding="utf-8")
        cv2.imwrite(f"output_layout_{i}.jpg", layout_vis)
