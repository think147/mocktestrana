"""
Extract highlighted correct answers from BIPARD.pdf and update questions.json.
The PDF has correct answers highlighted/marked. We need to detect these highlights
and map them back to the question options.
"""
import fitz  # PyMuPDF
import json
import os
import pathlib
import sys
import argparse
sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = "C:/Users/bipar/Downloads/BIPARD.pdf"
QUESTIONS_FILE = "questions.json"

def extract_highlights(pdf_path):
    """Extract all highlight annotations from the PDF."""
    doc = fitz.open(pdf_path)
    highlights = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get highlight annotations
        annots = page.annots()
        if annots:
            for annot in annots:
                annot_type = annot.type[0]
                # Type 8 = Highlight annotation
                if annot_type == 8:
                    # Get the highlighted text
                    rect = annot.rect
                    highlighted_text = page.get_text("text", clip=rect).strip()
                    highlights.append({
                        'page': page_num + 1,
                        'text': highlighted_text,
                        'rect': rect
                    })
    
    doc.close()
    return highlights

def extract_text_with_colors(pdf_path):
    """Extract text with color information to find highlighted/colored text."""
    doc = fitz.open(pdf_path)
    colored_texts = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    color = span["color"]
                    bgcolor = span.get("bgcolor", None)
                    flags = span.get("flags", 0)
                    
                    # Check for non-black text or special formatting
                    # Black is typically 0 or very close to 0
                    if text and color != 0:
                        colored_texts.append({
                            'page': page_num + 1,
                            'text': text,
                            'color': color,
                            'color_hex': f"#{color:06x}" if isinstance(color, int) else str(color),
                            'flags': flags
                        })
    
    doc.close()
    return colored_texts

def main():
    print(f"Opening PDF: {PDF_PATH}")
    print(f"File size: {os.path.getsize(PDF_PATH) / 1024 / 1024:.1f} MB")
    
    # Step 1: Check for highlight annotations
    print("\n=== Checking for highlight annotations ===")
    highlights = extract_highlights(PDF_PATH)
    print(f"Found {len(highlights)} highlight annotations")
    for h in highlights[:10]:
        print(f"  Page {h['page']}: '{h['text'][:80]}...' " if len(h['text']) > 80 else f"  Page {h['page']}: '{h['text']}'")
    
    # Step 2: Check for colored text
    print("\n=== Checking for colored/non-black text ===")
    colored = extract_text_with_colors(PDF_PATH)
    
    # Group by color
    color_groups = {}
    for c in colored:
        key = c['color_hex']
        if key not in color_groups:
            color_groups[key] = []
        color_groups[key].append(c)
    
    print(f"Found {len(colored)} colored text spans")
    for color_hex, items in sorted(color_groups.items(), key=lambda x: -len(x[1])):
        print(f"  Color {color_hex}: {len(items)} spans")
        for item in items[:3]:
            print(f"    Page {item['page']}: '{item['text'][:80]}'")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")
    
    # Step 3: Also check for background highlights via page drawings
    print("\n=== Checking page drawings/rectangles ===")
    doc = fitz.open(PDF_PATH)
    draw_count = 0
    for page_num in range(min(5, len(doc))):  # Check first 5 pages
        page = doc[page_num]
        drawings = page.get_drawings()
        for d in drawings:
            if d.get("fill"):  # Has fill color
                draw_count += 1
                if draw_count <= 10:
                    print(f"  Page {page_num+1}: fill={d['fill']}, rect={d.get('rect', 'N/A')}")
    doc.close()
    print(f"Total filled drawings in first 5 pages: {draw_count}")
    
    # New: Load questions and attempt to match colored text to options
    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as qf:
            questions = json.load(qf)
    except Exception as e:
        print("Failed to load questions JSON:", e)
        questions = []
    
    # Build a lookup of option text to question ID and option index
    option_lookup = {}
    for q in questions:
        for idx_opt, opt in enumerate(q.get('options', []), start=1):
            if opt:
                key = opt.strip().lower()
                option_lookup[key] = (q['id'], idx_opt)
    
    # Determine answers based on colored spans (choose most common matching option per question)
    answers = {}
    for c in colored:
        txt = c['text'].strip().lower()
        if txt in option_lookup:
            qid, opt_idx = option_lookup[txt]
            answers[qid] = opt_idx
    
    # Update questions with detected answers
    for q in questions:
        if q['id'] in answers:
            q['answer'] = answers[q['id']]
    
    # Write updated questions to a new file
    UPDATED_PATH = pathlib.Path(r'd:/MOCKTEST/questions_with_answers.json')
    with open(UPDATED_PATH, 'w', encoding='utf-8') as out_f:
        json.dump(questions, out_f, ensure_ascii=False, indent=2)
    print('Updated questions written to', UPDATED_PATH)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract answers from PDF')
    parser.add_argument('--run', action='store_true', help='Run the full extraction and answer detection')
    args = parser.parse_args()
    if args.run:
        main()
    else:
        print('Automatic run disabled. Use "--run" flag to execute the extraction.')
