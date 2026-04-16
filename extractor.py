import fitz  # PyMuPDF
import base64
import os
from pathlib import Path


def extract_from_pdf(pdf_path: str, label: str, output_dir: str = "extracted_images") -> dict:
    """
    Extract text and images from a PDF.
    Returns dict with 'text' and 'images' (list of base64 strings with captions).
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)

    full_text = ""
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract text
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += page.get_text()

        # Extract images
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            # Save image to disk
            img_filename = f"{label}_page{page_num+1}_img{img_index+1}.{ext}"
            img_path = os.path.join(output_dir, img_filename)
            with open(img_path, "wb") as f:
                f.write(image_bytes)

            # Also store as base64 for HTML embedding
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            images.append({
                "filename": img_filename,
                "path": img_path,
                "base64": b64,
                "ext": ext,
                "page": page_num + 1,
                "caption": f"{label} – Page {page_num + 1}, Image {img_index + 1}"
            })

    doc.close()
    return {"text": full_text, "images": images}
