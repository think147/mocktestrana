import pdfplumber, sys, os
pdf_path = r'C:\\Users\\bipar\\Downloads\\BIPARD.pdf'
output_path = r'd:\\MOCKTEST\\bipard_text.txt'
try:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print('Extracted to', output_path)
except Exception as e:
    print('Error:', e)
    sys.exit(1)
