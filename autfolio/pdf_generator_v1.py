#!/usr/bin/env python3
# pdf_generator.py
import os
import re
import sys
import time
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas

def register_fonts():
    """
    Try to register preferred custom fonts. Falls back to Helvetica if not found.
    Also attempts to register Arial from common system locations for header/footer.
    """
    heading_font = 'Helvetica-Bold'
    body_font = 'Helvetica'
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

    return heading_font, body_font

def setup_styles(heading_font, body_font):
    """Create and adjust paragraph styles (Heading3 is 25pt)."""
    styles = getSampleStyleSheet()

    styles['Heading1'].fontName = heading_font
    styles['Heading1'].fontSize = 30
    styles['Heading1'].leading = 36
    styles['Heading1'].spaceAfter = 20
    styles['Heading1'].textColor = white

    styles['Heading2'].fontName = heading_font
    styles['Heading2'].fontSize = 24
    styles['Heading2'].leading = 30
    styles['Heading2'].spaceAfter = 16
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
    styles['BodyText'].fontSize = 12
    styles['BodyText'].leading = 16
    styles['BodyText'].spaceAfter = 6   # reduced spacing between paragraphs
    styles['BodyText'].textColor = white

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
    
    Examples:
    - /Volumes/My Passport for Mac/Edits/... -> /Volumes/RYAN/Edits/...
    - /Volumes/SomeOtherDrive/Photos/... -> /Volumes/RYAN/Photos/...
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

def process_line(line, styles, story, missing_files=None):
    r"""
    Process a single line and add appropriate elements to story.

    - Strips markdown list/checkbox markers so image lines with markers become plain paths.
    - Un-escapes markdown punctuation & underscores (Google Docs) while preserving Windows paths.
    - Tight paragraph spacing and small image spacer.
    - Now includes fallback path functionality for missing images.
    """
    if line is None:
        return None

    raw = line.rstrip('\n')
    trimmed = raw.strip()

    # Un-escape punctuation and underscores but preserve Windows backslashes
    trimmed = clean_markdown_escapes(trimmed)

    # Strip list / checkbox markers (so "- [ ] /path/to/img.jpg" -> "/path/to/img.jpg")
    trimmed = strip_md_list_markers(trimmed)

    # Empty line -> small spacer
    if trimmed == '':
        story.append(Spacer(1, 6))
        return None

    # Headings
    if trimmed.startswith("### "):
        story.append(Paragraph(trimmed[4:], styles['Heading3']))
        return None
    elif trimmed.startswith("## "):
        story.append(Paragraph(trimmed[3:], styles['Heading2']))
        return None
    elif trimmed.startswith("# "):
        story.append(Paragraph(trimmed[2:], styles['Heading1']))
        return None

    # Code block (single backticks)
    if trimmed.startswith("`") and trimmed.endswith("`") and len(trimmed) >= 2:
        code_text = trimmed[1:-1]
        story.append(Paragraph(code_text, styles['Code']))
        return None

    # IMAGE detection: accept plain absolute/relative paths, including spaces.
    # Examples: /Volumes/RYAN/.../IMG.jpg , ./images/img.png , images/img.jpg , C:\path\img.jpg
    img_match = re.match(r'^(?:[A-Za-z]:\\|/|\./|\.?/)?(.+\.(jpg|jpeg|png|gif|bmp))\s*$', trimmed, re.IGNORECASE)
    if img_match:
        filepath = trimmed
        # normalize leading ./ if present
        if filepath.startswith('./'):
            filepath = filepath[2:]
        
        # Try to find the image file (original path or fallback)
        found_path, used_fallback = find_image_file(filepath)
        
        if found_path:
            try:
                img = Image(found_path)
                max_width, max_height = A4[0] - 100, A4[1] - 150
                img._restrictSize(max_width, max_height)
                story.append(img)
                story.append(Spacer(1, 12))  # space after images
                
                if used_fallback:
                    status_msg = f"✓ Image processed (fallback): {found_path}"
                    print(f"   📁 Used fallback path: {filepath} -> {found_path}")
                else:
                    status_msg = f"✓ Image processed: {found_path}"
                
                if missing_files is not None:
                    missing_files.append(status_msg)
                return status_msg
            except Exception as e:
                print(f"Warning: Could not process image {found_path}: {e}")
                story.append(Paragraph(f"[Image error: {found_path}]", styles['BodyText']))
                if missing_files is not None:
                    missing_files.append(filepath)
                return filepath
        else:
            # Check if we tried a fallback path
            fallback_path = find_fallback_path(filepath)
            if fallback_path:
                error_msg = f"[Image not found: {filepath} (also tried: {fallback_path})]"
            else:
                error_msg = f"[Image not found: {filepath}]"
            
            story.append(Paragraph(error_msg, styles['BodyText']))
            if missing_files is not None:
                missing_files.append(filepath)
            return filepath

    # Fallback bullet handling if original raw line had a marker (rare after stripping)
    if raw.lstrip().startswith("- ") or raw.lstrip().startswith("* "):
        bullet_text = trimmed.lstrip('-* ').strip()
        story.append(Paragraph(f"• {bullet_text}", styles['BodyText']))
        return None

    # Numbered list
    if re.match(r"^\d+\.\s", trimmed):
        story.append(Paragraph(trimmed, styles['BodyText']))
        return None

    # Regular paragraph: support **bold** and *italic*
    text = trimmed
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    story.append(Paragraph(text, styles['BodyText']))
    return None

class DarkPageTemplate(PageTemplate):
    def __init__(self, id, frames, document_title="", date="", header_font='Arial', **kwargs):
        PageTemplate.__init__(self, id, frames, **kwargs)
        self.document_title = document_title
        self.date = date
        self.header_font = header_font

    def beforeDrawPage(self, canvas, doc):
        canvas.saveState()

        # Black background
        canvas.setFillColor(black)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

        # Header/footer text in white
        canvas.setFillColor(white)

        # Choose Arial if registered, else Helvetica
        font_name = self.header_font if self.header_font in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        canvas.setFont(font_name, 6)  # 6pt as requested

        # Header: date (top-left) and optional title (top-center)
        canvas.drawString(50, A4[1] - 12, self.date)
        if self.document_title:
            canvas.drawCentredString(A4[0] / 2, A4[1] - 12, self.document_title)

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
        self.drawRightString(A4[0] - 50, 10, f"{page_num}/{total_pages}")

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

# Global document title (first ### heading)
document_title = ""

def build_pdf(input_file, output_file, date="June 2024"):
    global document_title

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return False, 0

    print("Setting up fonts and styles...")
    heading_font, body_font = register_fonts()
    styles = setup_styles(heading_font, body_font)

    header_font = 'Arial' if 'Arial' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'

    print("Creating PDF document structure...")

    # First pass: extract document title from first ### heading
    with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("### "):
                    document_title = clean_markdown_escapes(line.strip()[4:])
                    break

    # Create PDF document with dark theme
    doc = BaseDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=80,  # More space for header
        bottomMargin=60  # More space for footer
    )

    # Create a frame for content (adjusted for headers/footers)
    frame = Frame(50, 60, A4[0] - 100, A4[1] - 140, leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)

    # Add the dark page template with title and date
    dark_template = DarkPageTemplate(
        id='dark',
        frames=[frame],
        document_title=document_title,
        date=date,
        header_font=header_font
    )
    doc.addPageTemplates([dark_template])

    story = []
    missing_files = []  # Track missing files
    processed_images = 0  # Track successful image processing
    fallback_images = 0  # Track images found via fallback

    try:
        print("Reading input file...")
        processing_start = time.time()
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        print(f"Processing {total_lines} lines...")

        # Process lines with progress updates
        for line_num, raw_line in enumerate(lines, 1):
            try:
                result = process_line(raw_line, styles, story, missing_files)
                if result and "✓ Image processed" in result:
                    processed_images += 1
                    if "fallback" in result:
                        fallback_images += 1

                # Show progress every 10% or every 100 lines (whichever is smaller)
                progress_interval = min(100, max(1, total_lines // 10))
                if line_num % progress_interval == 0 or line_num == total_lines:
                    percentage = (line_num / total_lines) * 100
                    print(f"Progress: {line_num}/{total_lines} lines ({percentage:.1f}%)")

            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")
                story.append(Paragraph(raw_line.strip(), styles['BodyText']))

        processing_end = time.time()
        processing_time = processing_end - processing_start

        # Ensure "Ryan McLoughlin" is the first thing in the content
        if not story or not (hasattr(story[0], 'getPlainText') and story[0].getPlainText().strip() == "Ryan McLoughlin"):
            story.insert(0, Paragraph("Ryan McLoughlin", styles['Heading3']))

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

        if processed_images > 0:
            print(f"📸 Successfully processed {processed_images} images")
            if fallback_images > 0:
                print(f"📁 {fallback_images} images found using fallback paths")

        print()
        print("Building PDF document (this may take a moment)...")
        pdf_build_start = time.time()

        # Calculate total pages for footer (this is an approximation)
        estimated_pages = max(1, len(story) // 20)  # Rough estimate
        doc._total_pages = estimated_pages

        # Build the PDF
        doc.build(story, canvasmaker=NumberedCanvas)
        
        pdf_build_end = time.time()
        pdf_build_time = pdf_build_end - pdf_build_start
        total_time = pdf_build_end - processing_start
        
        print(f"✓ PDF successfully created: {output_file}")

        # Final summary with timing
        print()
        print("=== SUMMARY ===")
        if missing_files:
            actual_missing_count = len([f for f in missing_files if not f.startswith("✓")])
            if actual_missing_count > 0:
                print(f"⚠️  {actual_missing_count} files were missing and skipped")
        print(f"📄 PDF created with {len(story)} elements")
        if processed_images > 0:
            print(f"📸 {processed_images} images included")
            if fallback_images > 0:
                print(f"📁 {fallback_images} images found via fallback paths")
        if document_title:
            print(f"📖 Title: {document_title}")
        
        # Timing breakdown
        print(f"⏱️  Processing time: {format_duration(processing_time)}")
        print(f"⏱️  PDF build time: {format_duration(pdf_build_time)}")
        print(f"⏱️  Total execution time: {format_duration(total_time)}")

        return True, total_time

    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False, 0

def main():
    """Main entry point - uses hardcoded file names"""
    input_file = "testInput.md"
    output_file = "testOutput.pdf"
    date = "June 2024"  # Change this to your desired date

    print("=== Markdown to PDF Converter ===")
    print(f"Converting '{input_file}' to '{output_file}'...")
    print(f"Date: {date}")
    print()

    # Start overall timing
    start_time = time.time()
    success, build_time = build_pdf(input_file, output_file, date)
    end_time = time.time()
    
    # Total time includes any setup/cleanup outside of build_pdf
    total_script_time = end_time - start_time

    print()
    if success:
        print("🎉 Conversion completed successfully!")
    else:
        print("❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()