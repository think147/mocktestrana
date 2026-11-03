import fitz, os, sys
pdf='BIPARD.pdf'
if not os.path.exists(pdf):
    print('PDF missing')
    sys.exit(1)
doc=fitz.open(pdf)
count=0
bg_set=set()
for page in doc:
    for block in page.get_text('dict')['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for span in line['spans']:
                bg=span.get('bgcolor',0)
                if bg!=0:
                    count+=1
                    bg_set.add(bg)
print('non-zero bg count',count)
print('unique bg values',bg_set)
