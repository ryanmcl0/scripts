# Blog Workflow

This repo contains scripts I use to turn long-form travel photo-documentary projects into shareable, presentable and consise formats.  
The main goal: **reduce hundreds of hours of repetitive publishing work into a mostly automated flow**.

---

## 📌 Background & Problem

My workflow looks like this:

1. **Trips & Documentation**  
   - I return from each trip with *thousands* of RAW photos and long written accounts of my experiences, and reports and contextual information about the places.  
   - I write my stories in full across Google Docs, phone notes, and other drafts. When it's finished I compile them into one document.  
   - I can come back from a long trip with ~10,000 photos. These get filtered down to a few thousand that I would actually edit. Editing alone can involve ~1,000 final photos for a 2-week trip, requiring hundreds of hours in Lightroom.

2. **Publishing (old workflow)**  
   - I like having everything in one place: **text + photos combined into a single story**.  
   - Adobe Portfolio is my tool of choice - simple formatting options, 'unlimited' full resolution image hosting, free with Lighroom subscription, nice UI experience.
   - On Adobe Portfolio, this meant:  
     - Manually adding text sections  
     - Manually inserting photo grids for each section  
     - Repeating this across ~10,000+ words and ~1,000+ images for a blog from a trip
   - This added *many more hours* on top of writing and photo editing.

👉 The bottleneck: publishing was slow, inefficient, and draining.  
I was already spending a huge amount of time on writing and editing, I didn’t want to spend the same again just on layout and publishing.

For a 14,000-word trip write-up with ~1,000 photos, the whole process of culling, editing, writing and publishing would take hundreds of hours. Just from one trip. I already had a huge backlog and would never be able to catch up with existing and future trips. It was slow, inefficient, and unsustainable, especially after already putting hundreds of hours into writing and editing.

---

## 🚀 The Solution

I wanted to automate as much of this as possible, while keeping the same (or at least similar) final result I would have built manually in Adobe Portfolio.

### 1. Source File

I now create a "source file" that acts as a blueprint. Regardless of this flow, I already had what was close to a source file that could be parsed and processed anyway by exporting the Google Doc to markdown.
- It contains my full text.
- Between text sections, I insert **file paths** to the photos that correspond to that section.  
- This way, the structure of my story and the placement of images are defined once, in a single document.
- It's easy to bulk select the photos for a section in Finder, copy the pathnames and paste into the Doc.

### 2. PDF Generator

A script reads the source file, applies my layout and design preferences (inspired by my Portfolio style), and outputs a **PDF**.
- The PDF automatically builds the text + images together in the right order.  
- The script handles the repetitive layout work that I used to do manually.  
- The PDF is not 100% perfect yet, but it’s close to what I want.

One of my key requirments was to maintain image quality and resolution. Initially I used the full uncompressed JPGs, but it would take hours to build, produce a huge (10GB+) PDF and max out my CPU and RAM. I implemented compression to solve those problems, and the resulting images in the PDF are close to original quality (noticable loss only when tightly zoomed in) at a fraction of the file size and build time. 

### 3. PDF → Image Converter

Adobe Portfolio doesn’t support PDFs.  
The simplest workaround: **convert each PDF page into a high-resolution image** and import those.  

- Each page becomes either a JPEG (smaller, good for photo-heavy docs) or PNG (lossless, good for text-heavy docs).  
- Output filenames are sequential (`page_0001.jpg`, `page_0002.jpg`, …).  
- I can upload all these images at once into a Portfolio page, and it replicates my full story, with images, in order.  

Now, instead of hundreds of manual edits to compile my write ups and photos into one blog per trip, the publishing stage is **two script runs + one upload**.

---

## Features ✨

- **Custom Fonts & Dark Theme Formatting 🎨**  
  - Supports custom background, justification and fonts for headings and body text that automatically matches my existing style, design and layout preferences, but is still customisable.
  - *Why this matters:* Now I can automatically produce a near idential copy of what it would have been in Adobe Portfolio, without the manual effort. I now also have a hard copy saved on my hard drive, instead of only an online version on Adobe servers.

- **Chinese Text Support with Fallback 🇨🇳**  
  - Automatically detects Chinese text and switches to a compatible font.  
  - Prevents broken characters when the primary font doesn’t support Chinese.  
  - *Why this matters:* A lot of my writing includes Chinese place names and phrases. Without proper handling, they’d just show up as empty boxes. The script now switches fonts automatically, so the text flows properly directly from the source file.  

- **Image Handling with Compression 🖼️**  
  - Maintains image quality and resolution (similar to Adobe Portfolio).  
  - Compresses large image files (20MB+ each) to avoid maxing out RAM/CPU.  
  - Significantly reduces file size and speeds up PDF generation.  
  - *Why this matters:* One of my key requirements was to maintain image quality and resolution. Initially I used the full uncompressed JPGs, but it would take hours to build, produce a huge (10GB+) PDF and max out my CPU and RAM. I implemented compression to solve those problems, and the resulting images in the PDF are close to original quality (noticeable loss only when tightly zoomed in) at a fraction of the file size and build time.  

- **Runtime Logging ⏱️**  
  - Outputs total time taken to generate the PDF.  
  - Useful for comparing performance when making changes or optimizations.  
  - *Why this matters:* When playing around with compression levels, fonts, or layouts, build times can swing a lot. Having the runtime logged means I can quickly see if a change is making things faster or slower without having to guess.  

- **File Path Fallback 💾**  
  - Works across multiple hard drives and network storage.  
  - If a file isn’t found locally, it falls back to the network path automatically.  
  - *Why this matters:* My photos live across multiple drives. Without fallback paths, the script would constantly error out and build incorrectly if a filepath pointed to a drive that wasn't plugged in. Now it just checks my network storage (which contains everything) automatically, which keeps the workflow smooth. I can also build the blogs from anywhere with internet (even while travelling) by mounting my NAS via Tailscale.

- **Markdown Character Handling ✍️**  
  - Cleans up quirks from Google Docs → Markdown exports.  
  - Ensures formatting is preserved correctly in the final PDF.  
  - *Why this matters:* Exporting blog posts from Google Docs into Markdown isn’t clean — random characters and dodgy formatting can creep in. This can mess with the filepaths and result in images not being found. The script tidies this up so the layout looks clean straight away, and images are always found.  

- **Dynamic page numbering 📝** 
    - The script uses a custom `NumberedCanvas` class to track total page count and automatically insert "X of Y" on every page. This ensures accurate page numbers for even very large documents, without requiring a separate manual count or pre-calculation.

---

## ⚙️ Requirements

- Python 3.8+  
- Dependencies:  
  ```bash
  pip install pdf2image pillow reportlab
