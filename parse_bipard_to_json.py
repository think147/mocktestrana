import json, re, pathlib, sys

# Paths to the extracted text and the output JSON
TEXT_PATH = pathlib.Path(r'd:/MOCKTEST/bipard_text.txt')
OUTPUT_PATH = pathlib.Path(r'd:/MOCKTEST/questions.json')

if not TEXT_PATH.is_file():
    print('Text file not found:', TEXT_PATH)
    sys.exit(1)

text = TEXT_PATH.read_text(encoding='utf-8')

# Regex to capture each question block:
#   Question <num>: <question text>\n<options lines like "1. option" ...>
question_pattern = re.compile(r'Question\s+\d+:\s*(.*?)\n((?:\d+\.\s.*?\n)+)', re.DOTALL)

questions = []
for idx, match in enumerate(question_pattern.finditer(text), start=1):
    qtext = match.group(1).strip()
    options_block = match.group(2).strip()
    # Extract option texts (ignore leading numbers)
    opts = []
    for opt_line in options_block.splitlines():
        opt_match = re.match(r'\d+\.\s*(.*)', opt_line)
        if opt_match:
            opts.append(opt_match.group(1).strip())
    # Ensure exactly four options – pad with empty strings if needed
    while len(opts) < 4:
        opts.append('')
    question_entry = {
        "id": idx,
        "question": qtext,
        "options": opts[:4],
        "answer": -1,  # unknown – can be edited later
        "explanation": "",
    }
    questions.append(question_entry)

# Write the JSON file (pretty‑printed)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)
print('Written', len(questions), 'questions to', OUTPUT_PATH)
