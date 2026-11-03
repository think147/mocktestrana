import os
import json
import fitz  # PyMuPDF
import re

BASE = os.path.dirname(os.path.dirname(__file__))
QUESTIONS_PATH = os.path.join(BASE, 'questions.json')


def find_pdf():
    user = os.environ.get('USERPROFILE') or os.environ.get('HOME')
    if not user:
        raise RuntimeError('Cannot determine user home directory')
    candidate = os.path.join(user, 'Downloads', 'BIPARD.pdf')
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f'PDF not found at {candidate}')


def extract_highlights(pdf_path):
    doc = fitz.open(pdf_path)
    highlights = set()
    for p in doc:
        annot = p.first_annot
        while annot:
            if annot.type[0] == 8:  # highlight
                quads = annot.vertices
                if quads:
                    xs = [pt.x for quad in [quads[i:i+4] for i in range(0, len(quads), 4)] for pt in quad]
                    ys = [pt.y for quad in [quads[i:i+4] for i in range(0, len(quads), 4)] for pt in quad]
                    if xs and ys:
                        rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                        text = p.get_text("text", clip=rect).strip()
                        if text:
                            highlights.add(text.lower())
            annot = annot.next
    doc.close()
    return highlights


def parse_questions_from_text(full_text, highlights):
    """Extract questions in 'Question X:' format with numbered options 1-4"""
    items = []
    # Split by "Question \d+:" pattern
    parts = re.split(r'Question\s+\d+:\s*', full_text)
    
    for q_body in parts[1:]:  # skip preamble
        lines = q_body.split('\n')
        q_text = ''
        opts = []
        option_lines = {}
        
        in_options = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with 1., 2., 3., 4.
            opt_match = re.match(r'^([1-4])\.\s*(.+)$', line)
            if opt_match:
                opt_num = int(opt_match.group(1))
                opt_text = opt_match.group(2).strip()
                option_lines[opt_num] = opt_text
                in_options = True
            elif not in_options:
                # Accumulate question text
                q_text += ' ' + line
            else:
                # Continuation of previous option or new section
                if option_lines:
                    last_opt = max(option_lines.keys())
                    option_lines[last_opt] += ' ' + line
        
        q_text = re.sub(r'\s+', ' ', q_text.strip())
        
        # Validate we got all 4 options
        if len(option_lines) == 4 and q_text:
            opts = [option_lines.get(i, '').strip() for i in range(1, 5)]
            # Clean up options
            opts = [re.sub(r'\s+', ' ', o).strip() for o in opts]
            
            # Filter short options
            if not any(len(o) < 2 for o in opts):
                # Detect answer from highlights
                answer = None
                for idx, opt in enumerate(opts):
                    if opt.lower() in highlights:
                        answer = idx
                        break
                
                items.append({
                    'question': q_text,
                    'options': opts,
                    'answer': answer
                })
    
    return items


def load_bank():
    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_bank(bank):
    with open(QUESTIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)


def main():
    pdf = find_pdf()
    print('Found PDF:', pdf)
    
    highlights = extract_highlights(pdf)
    print(f'Extracted {len(highlights)} highlighted texts')

    # load PDF full text for parsing
    doc = fitz.open(pdf)
    full = ''
    for p in doc:
        full += p.get_text() + "\n"
    doc.close()

    parsed = parse_questions_from_text(full, highlights)
    print(f'Parsed {len(parsed)} clean questions from PDF')
    
    # Show sample
    if parsed:
        print(f'\nSample question:')
        print(f"  Q: {parsed[0]['question'][:80]}")
        print(f"  Options: {parsed[0]['options']}")
        print(f"  Answer index: {parsed[0]['answer']}")

    # Create fresh bank from PDF
    bank = []
    for idx, pq in enumerate(parsed, start=1):
        entry = {
            'id': idx,
            'question': pq['question'],
            'options': pq['options'],
            'answer': pq['answer']
        }
        bank.append(entry)

    save_bank(bank)
    print(f'\nReplaced questions.json with {len(bank)} clean questions from PDF.')


if __name__ == '__main__':
    main()
