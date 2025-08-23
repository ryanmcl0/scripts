#!/usr/bin/env python3
import os
from pdf2image import convert_from_path

def pdf_to_images(pdf_path, output_folder, dpi=300, image_format="JPEG"):
    """
    Converts each page of a PDF into high-resolution images.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_folder (str): Directory where images will be saved.
        dpi (int): Resolution in DPI (higher = sharper).
        image_format (str): "JPEG" or "PNG".
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"Converting {pdf_path} to {image_format} images...")
    pages = convert_from_path(pdf_path, dpi=dpi)

    for i, page in enumerate(pages, start=1):
        ext = "jpg" if image_format == "JPEG" else "png"
        output_filename = os.path.join(output_folder, f"page_{i:04d}.{ext}")

        if image_format == "JPEG":
            # High quality JPEG (minimal compression)
            page.save(output_filename, image_format, quality=100, subsampling=0)
        else:
            # PNG is lossless
            page.save(output_filename, image_format)

        print(f"Saved {output_filename}")

    print("✅ Conversion complete!")

if __name__ == "__main__":
    # === EDIT THESE VALUES ===
    pdf_path = "testOutput_compressed.pdf"                 # Path to PDF
    output_folder = "My_Portfolio_Images"  # Folder where images will be stored
    dpi = 300                              # Adjust DPI for resolution
    image_format = "PNG"                  # "JPEG" for smaller files, "PNG" for lossless

    pdf_to_images(pdf_path, output_folder, dpi, image_format)
