# extract_and_update_answers.py
"""Extract highlighted answer options from BIPARD.pdf and fill the "answer"
field in questions.json.

The PDF marks the correct answer with a background colour (highlight). This script
scans all pages, collects text spans whose `bgcolor` is non‑zero, and matches those
strings to the options of each question. When a match is found, the zero‑based index
of the option is stored in the "answer" field. The updated JSON is written back to
the same file.
"""

import fitz  # PyMuPDF
import json
import os
import sys

PDF_PATH = "C:/Users/bipar/Downloads/BIPARD.pdf"
QUESTIONS_PATH = "questions.json"

def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_questions(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_highlighted_texts(pdf_path):
    """Return a set of unique strings that appear with a non‑white background colour or as highlight annotations."""
    doc = fitz.open(pdf_path)
    highlighted = set()
    for page in doc:
        # Method 1: spans with non-zero background colour
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span.get("bgcolor", 0) != 0:
                        txt = span["text"].strip()
                        if txt:
                            highlighted.add(txt)
        # Method 2: highlight annotations (type 8)
        annots = page.annots()
        if annots:
            for annot in annots:
                if annot.type[0] == 8:
                    rect = annot.rect
                    txt = page.get_text("text", clip=rect).strip()
                    if txt:
                        highlighted.add(txt)
    doc.close()
    return highlighted

def map_answers(questions, highlighted_texts):
    """Update each question with the correct answer index.
    The function looks for a highlighted string that exactly matches one of the
    option texts (case‑insensitive, whitespace normalised). If a match is found,
    the index is stored in the ``answer`` field.
    """
    not_found = []
    for q in questions:
        if not q.get("options"):
            continue
        match_idx = None
        for idx, opt in enumerate(q["options"]):
            opt_norm = " ".join(opt.split()).lower()
            for hl in highlighted_texts:
                hl_norm = " ".join(hl.split()).lower()
                if opt_norm == hl_norm:
                    match_idx = idx
                    break
            if match_idx is not None:
                break
        if match_idx is not None:
            q["answer"] = match_idx
        else:
            not_found.append(q.get("id"))
    return not_found

def main():
    if not os.path.exists(PDF_PATH):
        print(f"PDF not found at {PDF_PATH}")
        sys.exit(1)
    if not os.path.exists(QUESTIONS_PATH):
        print(f"Questions file not found at {QUESTIONS_PATH}")
        sys.exit(1)

    print("Extracting highlighted texts from PDF…")
    highlighted_texts = extract_highlighted_texts(PDF_PATH)
    print(f"Found {len(highlighted_texts)} unique highlighted strings.")

    print("Loading questions JSON…")
    questions = load_questions(QUESTIONS_PATH)

    print("Mapping answers…")
    not_found = map_answers(questions, highlighted_texts)
    print(f"Updated answers for {len(questions) - len(not_found)} questions.")
    if not_found:
        print(f"Could not determine answer for {len(not_found)} questions (ids: {not_found[:20]}…)")

    print("Saving updated questions.json…")
    save_questions(QUESTIONS_PATH, questions)
    print("Done.")

if __name__ == "__main__":
    main()
