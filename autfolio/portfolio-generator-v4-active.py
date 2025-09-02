#!/usr/bin/env python3
# Enhanced PDF generator with smart collaging
import os
import re
import sys
import time
import io
import random

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

# Import PIL for image optimization
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
    print("✓ PIL/Pillow available for image optimization")
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  PIL/Pillow not available. Install with: pip install Pillow")
    print("   Images will be used without optimization (larger file sizes)")

# --- NEW: Enhanced Configuration for the flexible layout engine ---
LAYOUT_RANDOM_SEED = 1756844636       # Set to an integer for reproducible layouts, or None for random each run
MAX_IMAGES_PER_ROW = 3         # Maximum images allowed in a single collage row
PANORAMIC_ASPECT_RATIO = 2      # Aspect ratio (width/height) to consider an image panoramic
VERTICAL_ASPECT_RATIO_THRESHOLD = 0.9 # Aspect ratio (width/height) to consider an image vertical
LANDSCAPE_ASPECT_RATIO_THRESHOLD = 1.1 # <-- NEW: Aspect ratio to consider an image landscape
HORIZONTAL_MARGIN = 4               # Margin in points between images in the same row
VERTICAL_MARGIN = 4                 # NEW: Margin in points between image rows in a grid
DJI_DIPTYCH_MARGIN = 6          # Extra margin for DJI diptychs
LAYOUT_WEIGHTS = {
    '1': 0.18,  # 18% chance for a single full-width image row
    '2': 0.60,  # 60% chance for a two-image row
    '3': 0.22,  # 22% chance for a three-image row
}

# --- NEW: Constant for Pinyin characters with diacritics ---
PINYIN_CHARS = "āáǎàōóǒòēéěèīíǐìūúǔùǖǘǚǜüĀÁǍÀŌÓǑÒĒÉĚÈĪÍǏÌŪÚǓÙǕǗǙǛÜ"

def has_pinyin_or_chinese(text):
    """Check if text contains Chinese characters or Pinyin with diacritics."""
    if not text:
        return False
    # Check for any character that is either a Pinyin tone mark or a CJK ideograph
    for char in text:
        if char in PINYIN_CHARS or '\u4e00' <= char <= '\u9fff':
            return True
    return False

def has_chinese_characters(text):
    """Check if text contains Chinese characters (CJK Unified Ideographs)"""
    if not text:
        return False
    # Check for Chinese characters in the basic CJK range
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def register_fonts():
    """
    Try to register preferred custom fonts. Falls back to Helvetica if not found.
    Also attempts to register fonts that support Chinese characters.
    """
    heading_font = 'Helvetica-Bold'
    body_font = 'Helvetica'
    chinese_font = None
    
    # Try custom fonts (optional)
    try:
        if os.path.exists('/Library/Fonts/BebasKai.ttf'):
            pdfmetrics.registerFont(TTFont('BebasKai', '/Library/Fonts/BebasKai.ttf'))
        if os.path.exists('/Library/Fonts/FuturaCyrillicBook.ttf'):
            pdfmetrics.registerFont(TTFont('FuturaPT', '/Library/Fonts/FuturaCyrillicBook.ttf'))
            heading_font = 'BebasKai'
            body_font = 'FuturaPT'
    except Exception:
        pass

    # Try to register Arial for header/footer (best-effort)
    arial_paths = [
        '/Library/Fonts/Arial.ttf',                      # macOS
        '/System/Library/Fonts/Arial.ttf',               # alt macOS
        r'C:\Windows\Fonts\arial.ttf',                   # Windows
        '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',  # common Linux
        '/usr/share/fonts/truetype/msttcorefonts/arial.ttf'
    ]
    for p in arial_paths:
        try:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont('Arial', p))
                break
        except Exception:
            continue

    # Try to register fonts that support Chinese characters
    chinese_font_paths = [
        # macOS
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc', 
        '/Library/Fonts/Arial Unicode MS.ttf',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/STSong.ttf',
        
        # Windows
        r'C:\Windows\Fonts\simsun.ttc',
        r'C:\Windows\Fonts\msyh.ttc',
        r'C:\Windows\Fonts\simhei.ttf',
        r'C:\Windows\Fonts\simkai.ttf',
        
        # Linux (common Chinese font packages)
        '/usr/share/fonts/truetype/arphic/uming.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ]
    
    for font_path in chinese_font_paths:
        try:
            if os.path.exists(font_path):
                if font_path.endswith('.ttc'):
                    # TTC files may contain multiple fonts, try different subfont indices
                    for subfont_index in [0, 1, 2]:
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=subfont_index))
                            chinese_font = 'ChineseFont'
                            print(f"✓ Registered Chinese font: {font_path} (subfont {subfont_index})")
                            break
                        except Exception:
                            continue
                    if chinese_font:
                        break
                else:
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    chinese_font = 'ChineseFont'
                    print(f"✓ Registered Chinese font: {font_path}")
                    break
        except Exception as e:
            continue
    
    if not chinese_font:
        print("⚠️  No Chinese font found. Chinese characters may not display correctly.")
        chinese_font = body_font  # fallback to regular font

    return heading_font, body_font, chinese_font

def setup_styles(heading_font, body_font, chinese_font):
    """Create and adjust paragraph styles (Heading3 is 25pt)."""
    styles = getSampleStyleSheet()

    styles['Heading1'].fontName = heading_font
    styles['Heading1'].fontSize = 30
    styles['Heading1'].leading = 36
    styles['Heading1'].spaceAfter = 20
    styles['Heading1'].textColor = white

    styles['Heading2'].fontName = heading_font
    styles['Heading2'].fontSize = 20
    styles['Heading2'].leading = 30
    styles['Heading2'].spaceAfter = 6
    styles['Heading2'].textColor = white

    # Heading3 set to 25pt
    if 'Heading3' not in styles:
        styles.add(ParagraphStyle(
            'Heading3',
            parent=styles['Heading2'],
            fontName=heading_font,
            fontSize=25,
            leading=30,
            spaceAfter=20,
            textColor=white,
            alignment=TA_CENTER
        ))
    else:
        styles['Heading3'].fontName = heading_font
        styles['Heading3'].fontSize = 25
        styles['Heading3'].leading = 30
        styles['Heading3'].spaceAfter = 20
        styles['Heading3'].textColor = white
        styles['Heading3'].alignment = TA_CENTER

    # Body text tightened spacing
    styles['BodyText'].fontName = body_font
    styles['BodyText'].fontSize = 11
    styles['BodyText'].leading = 16
    styles['BodyText'].spaceAfter = 0   # reduced spacing between paragraphs (spacing comes default from new empty lines between sections in the source markdown file)
    styles['BodyText'].textColor = white

    # Chinese text style
    styles.add(ParagraphStyle(
        'ChineseText',
        parent=styles['BodyText'],
        fontName=chinese_font,
        fontSize=12,
        leading=16,
        spaceAfter=6,
        textColor=white
    ))

    # Chinese heading styles
    styles.add(ParagraphStyle(
        'ChineseHeading1',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=30,
        leading=36,
        spaceAfter=20,
        textColor=white
    ))

    styles.add(ParagraphStyle(
        'ChineseHeading2',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=24,
        leading=30,
        spaceAfter=16,
        textColor=white
    ))

    styles.add(ParagraphStyle(
        'ChineseHeading3',
        parent=styles['Heading3'],
        fontName=chinese_font,
        fontSize=25,
        leading=30,
        spaceAfter=20,
        textColor=white,
        alignment=TA_CENTER
    ))

    # Code style
    if 'Code' not in styles:
        styles.add(ParagraphStyle(
            'Code',
            parent=styles['BodyText'],
            fontName='Courier',
            fontSize=10,
            leading=14,
            leftIndent=20,
            backColor='#333333',
            textColor=white,
            spaceAfter=6
        ))

    return styles

def optimize_lightroom_image(image_path, max_width=2000, quality=92):
    """
    Optimize Lightroom 300 DPI exports for PDF use.
    Maintains print quality while dramatically reducing file size.
    
    Args:
        image_path: Path to the original image
        max_width: Maximum width in pixels (default 2000 for ~250 DPI on A4)
        quality: JPEG quality 1-100 (default 92 for visually lossless)
    
    Returns:
        BytesIO object with optimized image, or original path if optimization fails
    """
    if not PIL_AVAILABLE:
        return image_path
    
    try:
        with PILImage.open(image_path) as img:
            original_size = os.path.getsize(image_path)
            
            # Get original dimensions
            original_width, original_height = img.size
            
            # Preserve original if already smaller or similar size
            if original_width <= max_width:
                # Just optimize compression without resizing for smaller images
                if image_path.lower().endswith(('.jpg', '.jpeg')):
                    # Re-compress JPEG with our quality settings
                    img_buffer = io.BytesIO()
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = PILImage.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    
                    img.save(
                        img_buffer, 
                        format='JPEG', 
                        quality=quality, 
                        optimize=True,
                        progressive=True
                    )
                    img_buffer.seek(0)
                    
                    # Check if optimization actually helped
                    new_size = len(img_buffer.getvalue())
                    if new_size < original_size * 0.95:  # At least 5% reduction
                       # print(f"   📉 Optimized without resize: {original_size//1024}KB → {new_size//1024}KB")
                        return img_buffer
                
                # Return original if no significant improvement
                return image_path
            
            # Calculate new dimensions maintaining aspect ratio
            aspect_ratio = original_height / original_width
            new_width = max_width
            new_height = int(new_width * aspect_ratio)
            
            print(f"   📐 Resizing: {original_width}×{original_height} → {new_width}×{new_height}")
            
            # High-quality resize using Lanczos resampling (best quality)
            img_resized = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            
            # Convert RGBA/P to RGB if necessary (for JPEG compatibility)
            if img_resized.mode in ('RGBA', 'P', 'LA'):
                # Create white background for transparency
                background = PILImage.new('RGB', img_resized.size, (255, 255, 255))
                if img_resized.mode in ('RGBA', 'LA'):
                    # Handle transparency properly
                    background.paste(img_resized, mask=img_resized.split()[-1])
                else:
                    background.paste(img_resized)
                img_resized = background
            
            # Save with high quality JPEG compression
            img_buffer = io.BytesIO()
            img_resized.save(
                img_buffer, 
                format='JPEG', 
                quality=quality, 
                optimize=True,
                progressive=True  # Better for large images, loads progressively
            )
            img_buffer.seek(0)
            
            # # Log compression results
            # new_size = len(img_buffer.getvalue())
            # compression_ratio = (1 - new_size / original_size) * 100
            # print(f"   📉 Compressed: {original_size//1024}KB → {new_size//1024}KB ({compression_ratio:.1f}% reduction)")
            
            return img_buffer
            
    except Exception as e:
        print(f"   ⚠️  Error optimizing image {image_path}: {e}")
        return image_path  # Return original path as fallback

def get_image_aspect_ratio(image_path_or_buffer):
    """Get the aspect ratio of an image (width/height)"""
    if not PIL_AVAILABLE:
        return 1.5  # Assume landscape default
    
    try:
        #
# CORRECTED CODE
#
        if isinstance(image_path_or_buffer, io.BytesIO):
            image_path_or_buffer.seek(0) # Go to the start of the buffer
            img = PILImage.open(image_path_or_buffer)
            width, height = img.size
            image_path_or_buffer.seek(0)  # Reset the buffer for ReportLab to read later
        else:
            with PILImage.open(image_path_or_buffer) as img:
                width, height = img.size
        
        return width / height
    except Exception:
        return 1.5  # Default landscape aspect ratio

def create_image_row(image_data_list, max_width, max_height, custom_margin=None):
    """
    Creates a single row of images as a ReportLab Table with horizontal margins.
    All images in the row are scaled to the same height.
    Can accept a custom_margin, otherwise falls back to the global HORIZONTAL_MARGIN.
    """
    if not image_data_list:
        return None

    # Determine which margin value to use for this row
    margin = custom_margin if custom_margin is not None else HORIZONTAL_MARGIN

    num_images = len(image_data_list)

    # Calculate total margin width using the determined margin value
    total_margin_width = (num_images - 1) * margin if num_images > 1 else 0
    available_image_width = max_width - total_margin_width

    # Unpack the tuple, which may have 3 or 4 elements; we only need the second.
    total_aspect_ratio = sum(aspect_ratio for _, aspect_ratio, *_ in image_data_list)
    
    if total_aspect_ratio == 0:  # Avoid division by zero
        return None

    # Calculate the ideal height for images in this row, capped by max_height
    row_height = available_image_width / total_aspect_ratio
    if row_height > max_height:
        row_height = max_height

    row_data = []
    col_widths = []

    # Unpack the tuple, which may have 3 or 4 elements; we only need the first two.
    for i, (image_buffer, aspect_ratio, *_) in enumerate(image_data_list):
        img_width = row_height * aspect_ratio
        img = Image(image_buffer, width=img_width, height=row_height)
        
        row_data.append(img)
        col_widths.append(img_width)
        
        # Add a margin column after each image except the last one
        if i < num_images - 1:
            row_data.append(None)  # Empty cell for the margin
            col_widths.append(margin) # Use the determined margin value
            
    # Create a table with explicit column widths for images and margins
    table = Table([row_data], colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return table

def is_vertical_dji(image_data):
    """Check if an image is a vertical DJI image by aspect ratio and filename."""
    if not image_data:
        return False
    _, aspect_ratio, filepath, *_ = image_data
    is_vertical = aspect_ratio < VERTICAL_ASPECT_RATIO_THRESHOLD
    is_dji = "dji" in os.path.basename(filepath).lower()
    return is_vertical and is_dji

def is_landscape_dji(image_data):
    """Check if an image is a landscape DJI image by aspect ratio and filename."""
    if not image_data:
        return False
    _, aspect_ratio, filepath, *_ = image_data
    is_landscape = aspect_ratio >= LANDSCAPE_ASPECT_RATIO_THRESHOLD
    is_dji = "dji" in os.path.basename(filepath).lower()
    return is_landscape and is_dji

def create_dji_vertical_grid(image_data_list, max_width, max_height, custom_margin=None):
    """
    Creates a multi-row grid for 3 or 4 vertical DJI images with consistent
    horizontal and vertical margins. Returns a list of flowables.
    --- NEW: Now scales the entire grid down to fit within max_height if necessary. ---
    """
    num_images = len(image_data_list)
    if not (3 <= num_images <= 4):
        return None  # This function is only for 3 or 4 images

    margin = custom_margin if custom_margin is not None else HORIZONTAL_MARGIN
    
    # --- Step 1: Calculate initial dimensions without constraints ---
    initial_col_width = (max_width - margin) / 2
    top_row_data = image_data_list[:2]
    bottom_row_data = image_data_list[2:]

    top_row_height = 0
    if top_row_data:
        # Height of the row is determined by the tallest image in it
        top_row_height = max((initial_col_width / aspect_ratio) for _, aspect_ratio, *_ in top_row_data if aspect_ratio > 0)

    bottom_row_height = 0
    if bottom_row_data:
        bottom_row_height = max((initial_col_width / aspect_ratio) for _, aspect_ratio, *_ in bottom_row_data if aspect_ratio > 0)

    total_initial_height = top_row_height + bottom_row_height
    if bottom_row_data:
        total_initial_height += VERTICAL_MARGIN

    # --- Step 2: Check if scaling is needed and calculate final dimensions ---
    scale_factor = 1.0
    if total_initial_height > max_height:
        scale_factor = max_height / total_initial_height
    
    final_col_width = initial_col_width * scale_factor
    final_top_row_height = top_row_height * scale_factor
    final_bottom_row_height = bottom_row_height * scale_factor
    final_vertical_margin = VERTICAL_MARGIN * scale_factor

    # --- Step 3: Build the grid using the final, scaled dimensions ---
    grid_parts = []

    # Create the top row of images
    top_row_flowables = []
    for img_buf, aspect_ratio, *_ in top_row_data:
        img_w = final_top_row_height * aspect_ratio
        top_row_flowables.append(Image(img_buf, width=img_w, height=final_top_row_height))
    
    if len(top_row_flowables) == 2:
        top_row_flowables.insert(1, None)

    top_row_col_widths = [final_col_width, margin, final_col_width]
    top_row_table = Table([top_row_flowables], colWidths=top_row_col_widths)
    top_row_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    grid_parts.append(top_row_table)

    # Create the bottom row of images, if they exist
    if bottom_row_data:
        grid_parts.append(Spacer(1, final_vertical_margin))

        bottom_row_flowables = []
        for img_buf, aspect_ratio, *_ in bottom_row_data:
            img_w = final_bottom_row_height * aspect_ratio
            bottom_row_flowables.append(Image(img_buf, width=img_w, height=final_bottom_row_height))
        
        if len(bottom_row_flowables) == 2:
            bottom_row_flowables.insert(1, None)
            bottom_row_col_widths = [final_col_width, margin, final_col_width]
        else:
            bottom_row_col_widths = [final_col_width]
        
        bottom_row_table = Table([bottom_row_flowables], colWidths=bottom_row_col_widths)
        bottom_row_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        grid_parts.append(bottom_row_table)

    return grid_parts

def clean_markdown_escapes(line):
    r"""
    Un-escape common Markdown escapes produced by Google Docs exports,
    while preserving Windows-style backslashes.

    - Turn '\_' -> '_' (Google Docs commonly escapes underscores)
    - Remove backslashes before punctuation like '\-' -> '-', '\[' -> '[', '\.' -> '.'
    - DO NOT remove backslashes that precede letters/digits or a slash,
      so Windows paths like 'C:\Users\Ryan\...' remain unchanged.
    """
    if line is None:
        return line

    # 1) Specifically fix Google Docs escaping of underscores: '\_' -> '_'
    line = line.replace(r'\_', '_')

    # 2) Fix escaped dots (handles both '\.' and '\\.')
    line = line.replace(r'\.', '.').replace(r'\\.', '.')

    # 3) Remove backslash when it escapes punctuation (not word, not slash, not backslash)
    line = re.sub(r'\\([^\w/\\])', r'\1', line)

    return line

def strip_md_list_markers(line):
    """
    Remove leading markdown list or checkbox markers like:
      - item
      * item
      - [ ] item
      - [x] item
    Returns the stripped line.
    """
    return re.sub(r'^\s*[-*]\s*(?:\[\s*[xX]?\s*\])?\s*', '', line)

def find_fallback_path(original_path):
    """
    Create a fallback path by replacing any volume mount with /Volumes/RYAN/
    """
    if not original_path.startswith('/Volumes/'):
        return None
    
    # Find the end of the volume name (first slash after /Volumes/)
    parts = original_path.split('/')
    if len(parts) < 4:  # Need at least ['', 'Volumes', 'VolumeName', 'something']
        return None
    
    # Reconstruct path with /Volumes/RYAN/ as the base
    remaining_path = '/'.join(parts[3:])  # Everything after the volume name
    fallback_path = f'/Volumes/RYAN/{remaining_path}'
    
    return fallback_path

def find_image_file(filepath):
    """
    Try to find an image file, first at the original path, then at the fallback path.
    Returns (found_path, used_fallback) tuple.
    """
    # Try original path first
    if os.path.exists(filepath):
        return filepath, False
    
    # Try fallback path
    fallback_path = find_fallback_path(filepath)
    if fallback_path and os.path.exists(fallback_path):
        return fallback_path, True
    
    # Neither found
    return None, False

def get_appropriate_style(text, styles, style_prefix):
    """
    Choose the appropriate style based on whether text contains Chinese or Pinyin.
    For headings, still use Chinese styles if text contains such characters.
    """
    if has_pinyin_or_chinese(text):
        chinese_style_name = f"Chinese{style_prefix}"
        if chinese_style_name in styles:
            return styles[chinese_style_name]
        else:
            return styles.get('ChineseText', styles['BodyText'])
    else:
        return styles[style_prefix]

def handle_mixed_fonts(text, styles):
    """
    Handle text containing Chinese and/or Pinyin by wrapping those portions
    in the special Chinese font tag.
    """
    if not text or not has_pinyin_or_chinese(text):
        return text

    chinese_font = styles.get('ChineseText', styles['BodyText']).fontName
    result = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]
        if char in PINYIN_CHARS or '\u4e00' <= char <= '\u9fff':
            j = i
            while j < n and (text[j] in PINYIN_CHARS or '\u4e00' <= text[j] <= '\u9fff'):
                j += 1
            
            special_sequence = text[i:j]
            result.append(f'<font name="{chinese_font}">{special_sequence}</font>')
            i = j
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)

def is_image_line(line):
    """Check if a line starts with what looks like an image path."""
    trimmed = strip_md_list_markers(clean_markdown_escapes(line.strip()))
    # Match a path that ends in an image extension, allowing for text (like '1') after it.
    img_match = re.match(r'^(?:[A-Za-z]:\\|/|\./|\.?/)?.*?\.((jpg|jpeg|png|gif|bmp)(\s.*)?)$', trimmed, re.IGNORECASE)
    return img_match is not None

# --- NEW HELPER FUNCTION ---
def create_layouts_for_remaining_images(image_data_list, max_width, max_height, optimization_stats):
    """
    Arranges a list of standard (non-special-cased) images using weighted random logic.
    This is called by process_image_section AFTER high-priority images have been handled.
    """
    layouts = []
    if not image_data_list:
        return []

    print(f"      -> Arranging {len(image_data_list)} remaining image(s) with standard logic.")
    i = 0
    while i < len(image_data_list):
        remaining_images = len(image_data_list) - i
        if remaining_images == 1:
            target_row_size = 1
        else:
            possible_choices = [int(s) for s in LAYOUT_WEIGHTS.keys() if int(s) <= remaining_images]
            if not possible_choices: break
            weights = [LAYOUT_WEIGHTS[str(s)] for s in possible_choices]
            target_row_size = random.choices(possible_choices, weights=weights, k=1)[0]

        end_index = i + target_row_size
        current_row_data = image_data_list[i:end_index]

        if current_row_data:
            layouts.append(create_image_row(current_row_data, max_width, max_height))
            if len(current_row_data) > 1:
                optimization_stats['collages_created'] += 1
        i = end_index

    return layouts

def process_image_section(image_lines, styles, story, missing_files=None, optimization_stats=None, max_width=A4[0]-100, max_height=A4[1]-140):
    """
    Processes a single section of consecutive images, applying a multi-pass
    grouping strategy to collage images within this section.
    """
    if not image_lines:
        return

    print(f"   🖼️  Processing image section with {len(image_lines)} images...")
    
    # --- Step 1: Pre-process and validate all images in THIS section ---
    section_images_data = []
    for filepath, is_full_width in image_lines:
        if filepath.startswith('./'):
            filepath = filepath[2:]
        
        found_path, used_fallback = find_image_file(filepath)
        
        if found_path:
            try:
                log_msg = " (📌 Flagged for full-width)" if is_full_width else ""
                print(f"      - Processing: {os.path.basename(found_path)}{log_msg}")
                optimized_image = optimize_lightroom_image(found_path)
                aspect_ratio = get_image_aspect_ratio(optimized_image)
                
                # --- START DEBUG CODE BLOCK 1 ---
                # Check the result of the is_vertical_dji function directly
                # image_data_tuple_for_check = (optimized_image, aspect_ratio, found_path, is_full_width)
                # is_dji_check_result = is_vertical_dji(image_data_tuple_for_check)
                # print(f"      DEBUG: Image: {os.path.basename(found_path)}, Aspect Ratio: {aspect_ratio:.2f}, Is Vertical DJI? -> {is_dji_check_result}")
                # --- END DEBUG CODE BLOCK 1 ---
                
                section_images_data.append((optimized_image, aspect_ratio, found_path, is_full_width))
                
                if isinstance(optimized_image, io.BytesIO) and optimization_stats:
                    optimization_stats['optimized_count'] += 1
                elif optimization_stats:
                    optimization_stats['unchanged_count'] += 1
            except Exception as e:
                print(f"      ⚠️  Warning: Could not process image {found_path}: {e}")
                missing_files.append(filepath)
        else:
            error_msg = f"[Image not found: {filepath}]"
            story.append(Paragraph(error_msg, styles['BodyText']))
            missing_files.append(filepath)

    if not section_images_data:
        return

    # --- Step 2: Partition images WITHIN THIS SECTION by layout priority ---
    full_width_images = []
    dji_verticals = []
    dji_landscapes = []
    panoramics = []
    others = []

    for image_data in section_images_data:
        _, aspect_ratio, _, is_full_width = image_data

        if is_vertical_dji(image_data):
            dji_verticals.append(image_data)
        elif is_full_width:
            full_width_images.append(image_data)
        elif is_landscape_dji(image_data):
            dji_landscapes.append(image_data)
        elif aspect_ratio >= PANORAMIC_ASPECT_RATIO:
            panoramics.append(image_data)
        else:
            others.append(image_data)
    
    # --- START DEBUG CODE BLOCK 2 ---
    print("\n      --- DEBUG: Image Partitioning Summary for this Section ---")
    print(f"      - Full-Width Images: {len(full_width_images)}")
    print(f"      - Vertical DJI Images found for collaging: {len(dji_verticals)}")
    print(f"      - Landscape DJI Images: {len(dji_landscapes)}")
    print(f"      - Panoramics: {len(panoramics)}")
    print(f"      - Other Images (to be arranged normally): {len(others)}")
    print("      --------------------------------------------------------\n")
    # --- END DEBUG CODE BLOCK 2 ---
            
    # --- Step 3: Generate layouts for this section in order of priority ---
    section_layouts = []

    # Priority 1: All vertical DJI images in this section are grouped first.
    if dji_verticals:
        print(f"      -> Prioritizing {len(dji_verticals)} vertical DJI image(s) in this section.")
        dji_leftovers = []
        for i in range(0, len(dji_verticals), 4):
            chunk = dji_verticals[i:i+4]
            
            if len(chunk) == 2:
                print(f"         -> Creating a 2-image side-by-side row (same height).")
                # Pass the special margin only for this specific case
                row_layout = create_image_row(chunk, max_width, max_height, custom_margin=DJI_DIPTYCH_MARGIN)
                if row_layout:
                    section_layouts.append(row_layout)
                    optimization_stats['collages_created'] += 1
            elif len(chunk) >= 3:
                print(f"         -> Creating a {len(chunk)}-image grid.")
                # Pass the special margin to the grid function as well
                grid = create_dji_vertical_grid(chunk, max_width, max_height, custom_margin=DJI_DIPTYCH_MARGIN)
                if grid:
                    section_layouts.append(KeepTogether(grid))
                    optimization_stats['collages_created'] += 1
            else:
                dji_leftovers.extend(chunk)
        
        if dji_leftovers:
            others.extend(dji_leftovers)

    # Priority 2: User-flagged full-width images.
    if full_width_images:
        print(f"      -> Processing {len(full_width_images)} full-width image(s).")
        for image in full_width_images:
            section_layouts.append(create_image_row([image], max_width, max_height))

    # Priority 3: Panoramics.
    if panoramics:
        print(f"      -> Processing {len(panoramics)} panoramic image(s).")
        for pano in panoramics:
            section_layouts.append(create_image_row([pano], max_width, max_height))

    # Priority 4: DJI Landscapes.
    if dji_landscapes:
        print(f"      -> Processing {len(dji_landscapes)} landscape DJI image(s).")
        for dji_land in dji_landscapes:
            section_layouts.append(create_image_row([dji_land], max_width, max_height))

    # Finally, process all remaining images from this section.
    if others:
        remaining_layouts = create_layouts_for_remaining_images(others, max_width, max_height, optimization_stats)
        section_layouts.extend(remaining_layouts)

    # --- Step 4: Append all generated layouts for this section to the story ---
    for layout in section_layouts:
        story.append(layout)
        story.append(Spacer(1, 10)) # Change 10 to VERTICAL_MARGIN for equal vertical and horizontal spacing
    
    print(f"      -> Created {len(section_layouts)} layout(s) for this section.")

# --- REWRITTEN process_lines_with_collaging to use the new section-based logic ---
def process_lines_with_collaging(lines, styles, story, missing_files=None, optimization_stats=None, frame_width=A4[0]-100, frame_height=A4[1]-140):
    """
    Process lines, identifying consecutive image sections and processing them
    one section at a time to preserve separation by text content.
    Also calculates word count for non-image lines.
    """
    i = 0
    total_lines = len(lines)
    
    img_pattern = re.compile(r'^(.*?\.(?:jpg|jpeg|png|gif|bmp))\s*(\{.*\})?\s*$', re.IGNORECASE)

    while i < total_lines:
        line = lines[i].rstrip('\n')
        
        progress_interval = min(50, max(1, total_lines // 20))
        if i % progress_interval == 0 or i == total_lines - 1:
            percentage = ((i + 1) / total_lines) * 100
            print(f"Progress: Parsing line {i+1}/{total_lines} ({percentage:.1f}%)")
        
        if is_image_line(line):
            image_section = []
            
            while i < total_lines and is_image_line(lines[i]):
                line_content = strip_md_list_markers(clean_markdown_escapes(lines[i].strip()))
                match = img_pattern.match(line_content)
                
                if match:
                    filepath = match.group(1).strip()
                    attributes_str = match.group(2)
                    is_full_width = bool(attributes_str and 'layout=full' in attributes_str)
                    image_section.append((filepath, is_full_width))
                else:
                    image_section.append((line_content, False))
                i += 1
            
            # --- PROCESS THE IDENTIFIED SECTION IMMEDIATELY ---
            process_image_section(image_section, styles, story, missing_files, optimization_stats, max_width=frame_width, max_height=frame_height)
            continue
        
        # --- NEW: Word Count Logic for non-image lines ---
        if optimization_stats is not None:
            # Clean the line for word counting
            # 1. Strip markdown markers and escapes
            text_for_count = strip_md_list_markers(clean_markdown_escapes(line.strip()))
            # 2. Remove heading markers (e.g., ### text -> text)
            text_for_count = re.sub(r'^\s*#+\s*', '', text_for_count)
            # 3. Remove bold/italic/code markers
            text_for_count = re.sub(r'(\*\*|\*|`)', '', text_for_count)
            
            # Count words if the line is not empty after cleaning
            if text_for_count:
                optimization_stats['word_count'] += len(text_for_count.split())

        # --- Process text lines for PDF generation ---
        trimmed = clean_markdown_escapes(line.strip())
        trimmed = strip_md_list_markers(trimmed)

        if trimmed == '':
            if i > 0:
                previous_line_trimmed = clean_markdown_escapes(lines[i-1].strip())
                if previous_line_trimmed.startswith(('# ', '## ', '### ')):
                    pass
                else:
                    story.append(Spacer(1, 6))
            else:
                story.append(Spacer(1, 6))
        elif trimmed.startswith("### "):
            heading_text = trimmed[4:]
            style = get_appropriate_style(heading_text, styles, 'Heading3')
            story.append(Paragraph(heading_text, style))
        elif trimmed.startswith("## "):
            heading_text = trimmed[3:]
            style = get_appropriate_style(heading_text, styles, 'Heading2')
            story.append(Paragraph(heading_text, style))
        elif trimmed.startswith("# "):
            heading_text = trimmed[2:]
            style = get_appropriate_style(heading_text, styles, 'Heading1')
            story.append(Paragraph(heading_text, style))
        elif trimmed.startswith("`") and trimmed.endswith("`") and len(trimmed) >= 2:
            code_text = trimmed[1:-1]
            story.append(Paragraph(code_text, styles['Code']))
        elif line.lstrip().startswith("- ") or line.lstrip().startswith("* "):
            bullet_text = trimmed.lstrip('-* ').strip()
            text_with_mixed_fonts = handle_mixed_fonts(f"• {bullet_text}", styles)
            story.append(Paragraph(text_with_mixed_fonts, styles['BodyText']))
        elif re.match(r"^\d+\.\s", trimmed):
            text_with_mixed_fonts = handle_mixed_fonts(trimmed, styles)
            story.append(Paragraph(text_with_mixed_fonts, styles['BodyText']))
        else:
            text = trimmed
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            text_with_mixed_fonts = handle_mixed_fonts(text, styles)
            story.append(Paragraph(text_with_mixed_fonts, styles['BodyText']))
        
        i += 1


class DarkPageTemplate(PageTemplate):
    def __init__(self, id, frames, document_title="", date="", header_font='Arial', pagesize=A4, **kwargs):
        PageTemplate.__init__(self, id, frames, **kwargs)
        self.document_title = document_title
        self.date = date
        self.header_font = header_font
        self.page_width, self.page_height = pagesize

    def beforeDrawPage(self, canvas, doc):
        canvas.saveState()

        # Black background
        canvas.setFillColor(black)
        canvas.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        # Header/footer text in white
        canvas.setFillColor(white)

        # Choose Arial if registered, else Helvetica
        font_name = self.header_font if self.header_font in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        canvas.setFont(font_name, 6)  # 6pt as requested

        # Header: date (top-left) and optional title (top-center)
        canvas.drawString(50, self.page_height - 12, self.date)
        if self.document_title:
            canvas.drawCentredString(self.page_width / 2, self.page_height - 12, self.document_title)

        # Footer: just URL (page numbers handled by NumberedCanvas)
        canvas.drawString(50, 10, "https://ryanmcl.myportfolio.com/")

        canvas.restoreState()

class NumberedCanvas(canvas.Canvas):
    """
    Canvas subclass that knows total page count.
    First stores page states, then draws page numbers with 'X of Y'.
    """
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Calculate page count and write 'X of Y' in all pages."""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, total_pages):
        """Actually draw the page number in footer."""
        page_num = self._pageNumber
        self.setFillColor(white)
        font_name = 'Arial' if 'Arial' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        self.setFont(font_name, 6)
        self.drawRightString(self._pagesize[0] - 50, 10, f"{page_num}/{total_pages}")

def format_duration(seconds):
    """Format duration in a human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"

def format_file_size(bytes_size):
    """Format file size in human-readable format"""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f}KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f}MB"
    else:
        return f"{bytes_size/(1024*1024*1024):.1f}GB"

# Global document title (first ### heading)
document_title = ""

def build_pdf(input_file, output_file, date="June 2024", optimization_stats=None, page_dims=A4):
    global document_title

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return False, 0

    # --- NEW: Use passed-in dict or create a default ---
    if optimization_stats is None:
        optimization_stats = {
            'optimized_count': 0,
            'unchanged_count': 0,
            'collages_created': 0,
            'word_count': 0
        }

    print("Setting up fonts and styles...")
    heading_font, body_font, chinese_font = register_fonts()
    styles = setup_styles(heading_font, body_font, chinese_font)

    header_font = 'Arial' if 'Arial' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'

    print("Creating PDF document structure...")

    # First pass: extract document title from first ### heading
    with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("### "):
                    document_title = clean_markdown_escapes(line.strip()[4:])
                    break
    
    # Extract page dimensions
    page_width, page_height = page_dims

    # Create PDF document with dark theme and compression
    left_margin, right_margin = 50, 50
    top_margin, bottom_margin = 80, 60

    doc = BaseDocTemplate(
        output_file,
        pagesize=page_dims,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        compress=True  # Enable PDF compression for smaller file size
    )

    # Calculate frame dimensions based on page size and margins
    frame_width = page_width - left_margin - right_margin
    frame_height = page_height - top_margin - bottom_margin

    # Create a frame for content (adjusted for headers/footers)
    frame = Frame(left_margin, bottom_margin, frame_width, frame_height, leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)

    # Add the dark page template with title and date
    dark_template = DarkPageTemplate(
        id='dark',
        frames=[frame],
        document_title=document_title,
        date=date,
        header_font=header_font,
        pagesize=page_dims
    )
    doc.addPageTemplates([dark_template])

    story = []
    missing_files = []  # Track missing files
    
    try:
        print("Reading input file...")
        processing_start = time.time()
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        print(f"Processing {total_lines} lines with smart collaging...")
        
        if PIL_AVAILABLE:
            print("📸 Image optimization enabled - this will reduce file size significantly")
        else:
            print("⚠️  Image optimization disabled - install Pillow for smaller files")

        print("🎨 Smart collaging enabled - consecutive images will be grouped when beneficial")

        # Process lines with collaging support
        process_lines_with_collaging(lines, styles, story, missing_files, optimization_stats, frame_width=frame_width, frame_height=frame_height)

        processing_end = time.time()
        processing_time = processing_end - processing_start

        # Ensure "Ryan McLoughlin" is the first thing in the content
        if not story or not (hasattr(story[0], 'getPlainText') and story[0].getPlainText().strip() == "Ryan McLoughlin"):
            story.insert(0, Paragraph("Ryan McLoughlin", styles['Heading3']))

        # Report on optimization results
        total_images = optimization_stats['optimized_count'] + optimization_stats['unchanged_count']
        print()
        if total_images > 0 or optimization_stats['word_count'] > 0:
            print(f"📊 CONTENT PROCESSING SUMMARY:")
            if total_images > 0:
                print(f"   📸 Total images processed: {total_images}")
                print(f"   ✅ Images optimized: {optimization_stats['optimized_count']}")
                print(f"   ➖ Images unchanged: {optimization_stats['unchanged_count']}")
                if optimization_stats.get('collages_created', 0) > 0:
                    print(f"   🎨 Collage/grid layouts created: {optimization_stats['collages_created']}")
            if optimization_stats['word_count'] > 0:
                print(f"   ✍️  Text content word count: {optimization_stats['word_count']} words")

        # Report on missing files
        print()
        if missing_files:
            actual_missing = [f for f in missing_files if not f.startswith("✓")]
            if actual_missing:
                print(f"⚠️  {len(actual_missing)} missing files found:")
                for missing_file in actual_missing:
                    print(f"   ❌ {missing_file}")
            else:
                print("✅ All referenced files were found!")
        else:
            print("✅ All referenced files were found!")

        print()
        print("Building PDF document (this may take a moment)...")
        pdf_build_start = time.time()

        # Build the PDF
        doc.build(story, canvasmaker=NumberedCanvas)
        
        pdf_build_end = time.time()
        pdf_build_time = pdf_build_end - pdf_build_start
        total_time = pdf_build_end - processing_start
        
        # Get final file size
        if os.path.exists(output_file):
            final_file_size = os.path.getsize(output_file)
            print(f"✓ PDF successfully created: {output_file}")
            print(f"📁 Final file size: {format_file_size(final_file_size)}")
        else:
            print(f"✓ PDF successfully created: {output_file}")

        print()
        print("=== FINAL SUMMARY ===")
        print(f"📖 Title: {document_title}" if document_title else "📖 Title: Not specified")
        print(f"📄 PDF created with {len(story)} elements")
        if total_images > 0:
            print(f"📸 {total_images} images processed ({optimization_stats['optimized_count']} optimized)")
            if optimization_stats.get('collages_created', 0) > 0:
                print(f"🎨 {optimization_stats['collages_created']} image collage/grid layouts created")
        
        # Timing breakdown
        print(f"⏱️  Processing time: {format_duration(processing_time)}")
        print(f"⏱️  PDF build time: {format_duration(pdf_build_time)}")
        print(f"⏱️  Total execution time: {format_duration(total_time)}")
        
        return True, total_time

    except Exception as e:
        print(f"Error creating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def pre_check_duplicates(input_file_path):
    """
    Scans the input Markdown file for duplicate image paths and warns the user.
    Returns True if the user wants to continue.
    """
    print("--- Pre-check: Scanning for duplicate image paths ---")
    image_locations = {}
    
    if not os.path.exists(input_file_path):
        print(f"Error: Input file '{input_file_path}' not found.")
        return False

    with open(input_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex to extract just the path, similar to the one in process_lines
    img_pattern = re.compile(r'^(.*?\.(?:jpg|jpeg|png|gif|bmp))', re.IGNORECASE)

    for i, line in enumerate(lines, 1):
        if is_image_line(line):
            # Clean up the line to get just the path
            clean_line = strip_md_list_markers(clean_markdown_escapes(line.strip()))
            match = img_pattern.match(clean_line)
            if match:
                filepath = match.group(1).strip()
                if filepath not in image_locations:
                    image_locations[filepath] = []
                image_locations[filepath].append(i)

    # Find and report duplicates
    duplicates_found = {path: lines for path, lines in image_locations.items() if len(lines) > 1}

    if not duplicates_found:
        print("✓ No duplicate image paths found. Proceeding...\n")
        return True
    else:
        print(f"⚠️  Warning: {len(duplicates_found)} duplicate image path(s) found.")
        print("   This may be intentional, but please review the list below.")
        for path, line_nums in sorted(duplicates_found.items()):
            print(f"   - Path: {os.path.basename(path)}")
            print(f"     Found on lines: {', '.join(map(str, line_nums))}")
        
        try:
            input("\nPress Enter to continue with the PDF generation, or Ctrl+C to abort...")
            print() # Add a newline for better spacing after user presses Enter
            return True
        except KeyboardInterrupt:
            print("\n❌ User aborted the process.")
            return False

def main():
    """Main entry point - uses input from 'source_files' and outputs to 'outputs' folder"""
    input_dir = "source_files"
    input_file_name = "China 2025 North test1.md"
    input_file = os.path.join(input_dir, input_file_name)

    seed_was_specified = LAYOUT_RANDOM_SEED is not None
    if not seed_was_specified:
        # No seed is specified, so generate a new one for this run
        current_seed = int(time.time())
    else:
        # A seed has been specified, use it
        current_seed = LAYOUT_RANDOM_SEED
    
    # Apply the seed to the random number generator so it affects the layout
    random.seed(current_seed)
    
    # Apply the seed to the random number generator
    random.seed(current_seed)
    
    # --- PAGE SIZE SELECTION ---
    # Choose one of the following options by uncommenting the desired block.
    
    # 1. Standard A4 Portrait (Default)
    page_size_name = "A4_Portrait_seed"
    page_size = A4
    
    # 2. A4 Landscape
    # page_size_name = "A4_Landscape"
    # page_size = landscape(A4)
    
    # 3. Custom Size (e.g., 170mm x 240mm)
    # page_size_name = "170x240mm"
    # page_size = (170*mm, 240*mm)

    # Create outputs folder if it doesn't exist
    output_dir = "output_gemini"
    os.makedirs(output_dir, exist_ok=True)

    # Generate output file path with same base name as input
    base_name = os.path.splitext(input_file_name)[0]
    output_file = os.path.join(output_dir, f"{base_name}_{page_size_name}.pdf")

    date = "February 2025 Chinese New Year"  # Change this to your desired date

    print("=== Optimized Markdown to PDF Converter with Smart Collaging ===")
    
    # --- Run pre-check for duplicate images ---
    if not pre_check_duplicates(input_file):
        sys.exit(1)

    print(f"Converting '{input_file}' to '{output_file}'...")
    print(f"Date: {date}\n")

    if PIL_AVAILABLE:
        print("🚀 Image optimization enabled - expect significantly smaller file sizes!")
        print("🎨 Smart collaging enabled - multiple images will be grouped for better layout!\n")
    else:
        print("⚠️ Image optimization unavailable - install Pillow for best results")
        print("🎨 Smart collaging enabled - layout will be optimized even without image optimization\n")

    # --- Stats dict created here to be passed around ---
    final_stats = {
        'optimized_count': 0,
        'unchanged_count': 0,
        'collages_created': 0,
        'word_count': 0
    }

    # Start overall timing
    start_time = time.time()
    success, build_time = build_pdf(input_file, output_file, date, final_stats, page_dims=page_size)
    end_time = time.time()
    
    print()
    if success:
        print("🎉 Conversion completed successfully!")

        print() # Add a blank line for spacing
        if not seed_was_specified:
            print(f"🌱 A new random layout was generated using seed: {current_seed}")
            print("   To reuse this exact layout, set LAYOUT_RANDOM_SEED in the script to this number.")
        else:
            print(f"🌱 The layout was generated using the specified seed: {current_seed}")

        # --- Word count in final summary ---
        if final_stats['word_count'] > 0:
            print(f"✍️  Document word count: {final_stats['word_count']} words")
        print(f"⏱️ Total script execution time: {format_duration(build_time)}")

        # --- Word count in final summary ---
        if final_stats['word_count'] > 0:
            print(f"✍️  Document word count: {final_stats['word_count']} words")
        print(f"⏱️ Total script execution time: {format_duration(build_time)}")
        print()
        print("💡 The collaging system groups consecutive images for:")
        print("   • More professional presentation")
        print("   • Shorter document length")
        print("   • Better use of page space")
    else:
        print("❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()