import cv2

from yomitoku import OCR
from yomitoku.data.functions import load_pdf
from yomitoku.export import save_json

if __name__ == "__main__":
    ocr = OCR(visualize=True, device="cuda")
    # PDFファイルを読み込み
    imgs = load_pdf("demo/sample.pdf")
    import time

    start = time.time()
    for i, img in enumerate(imgs):
        results, ocr_vis = ocr(img)

        # JSON形式で解析結果をエクスポート
        save_json(results, f"output_{i}.json", encoding="utf-8")
        cv2.imwrite(f"output_ocr_{i}.jpg", ocr_vis)
