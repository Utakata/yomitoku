import os
from io import BytesIO
from PIL import Image
import weasyprint
import pypdfium2 as pdfium
import numpy as np

from ..export.export_html import create_html_from_ocr_result
from ..constants import ROOT_DIR


def create_searchable_pdf(images, ocr_results, output_path, font_path=None):
    """
    Creates a searchable PDF from a list of images and their corresponding OCR results.
    This new implementation uses WeasyPrint to generate tagged PDFs from HTML,
    ensuring proper reading order for accessibility.
    """
    # Create a new empty PDF document to which pages will be added.
    final_pdf = pdfium.PdfDocument.new()

    # Get the project's root directory to resolve the font path correctly.
    font_path = os.path.join(ROOT_DIR, "resource/MPLUS1p-Medium.ttf")
    font_config = f"""
    @font-face {{
        font-family: 'MPLUS1p-Medium';
        src: url('file://{font_path}');
    }}
    body, div {{
        font-family: 'MPLUS1p-Medium';
    }}
    """

    for i, (image_np, ocr_result) in enumerate(zip(images, ocr_results)):
        # Convert numpy array (BGR) to PIL Image (RGB)
        image = Image.fromarray(image_np[:, :, ::-1])
        w, h = image.size

        # Save the image to a temporary file to be used as a background
        temp_image_path = f"temp_page_{i}.png"
        image.save(temp_image_path)

        # Generate the HTML content with transparent, positioned text
        html_content = create_html_from_ocr_result(ocr_result, (w, h))

        # CSS to set the page size, use the image as a background, and load the font.
        css_content = f"""
        @page {{
            size: {w}px {h}px;
            margin: 0;
        }}
        body {{
            background-image: url('file://{os.path.abspath(temp_image_path)}');
            background-repeat: no-repeat;
            background-size: cover;
            width: {w}px;
            height: {h}px;
            margin: 0;
        }}
        """

        # Generate the PDF for the current page in memory
        html = weasyprint.HTML(string=html_content)
        css_page = weasyprint.CSS(string=css_content)
        css_font = weasyprint.CSS(string=font_config)

        # We need to provide the font configuration to WeasyPrint
        page_pdf_bytes = html.write_pdf(stylesheets=[css_page, css_font])

        # Load the generated single-page PDF into pypdfium2
        page_pdf = pdfium.PdfDocument(page_pdf_bytes)

        # Import the page into the final PDF document
        final_pdf.import_pages(page_pdf)

        # Clean up the temporary image file and close the page PDF
        page_pdf.close()
        os.remove(temp_image_path)

    # Save the final combined PDF
    final_pdf.save(output_path)
    final_pdf.close()