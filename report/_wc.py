import re, sys

with open('report.typ','r',encoding='utf-8') as f:
    src = f.read()

matches = list(re.finditer(r'(?m)^= (.+)$', src))
spans = []
for i, m in enumerate(matches):
    end = matches[i+1].start() if i+1 < len(matches) else len(src)
    spans.append((m.group(1), m.start(), end))

WORD_RE = re.compile(r"[A-Za-z0-9'£\-]+")

def count_section(body: str):
    # Strip block comments (//...)
    body = re.sub(r'//[^\n]*', '', body)

    # Pull captions out before nuking figure blocks
    captions = re.findall(r'caption:\s*\[([^\]]*)\]', body)
    body = re.sub(r'#figure\([\s\S]*?\)\s*<[^>]+>', ' ', body)

    # Pull table cell contents (anything inside [ ] inside a #table call)
    table_cells = []
    for tbl in re.findall(r'#table\(([\s\S]*?)\)\s*', body):
        table_cells += re.findall(r'\[([^\[\]]*)\]', tbl)
    body = re.sub(r'#table\([\s\S]*?\)\s*', ' ', body)

    # Drop math blocks $...$
    body = re.sub(r'\$[\s\S]*?\$', ' ', body)

    # Drop labels <...>
    body = re.sub(r'<[^>]+>', ' ', body)

    # Drop typst function-ish markup remnants
    body = re.sub(r'#[A-Za-z_][A-Za-z0-9_]*', ' ', body)
    body = re.sub(r'[\[\]\(\)]', ' ', body)

    body_words = len(WORD_RE.findall(body))
    caption_words = sum(len(WORD_RE.findall(c)) for c in captions)
    table_words = sum(len(WORD_RE.findall(c)) for c in table_cells)
    return body_words, caption_words, table_words

print(f"{'Section':50s} {'Body':>6s} {'Caps':>6s} {'Tbl':>6s} {'Total':>7s}")
print('-'*80)
for title, start, end in spans:
    b, c, t = count_section(src[start:end])
    print(f"{title[:50]:50s} {b:6d} {c:6d} {t:6d} {b+c+t:7d}")
