"""
Sync homepage card labels (date + reading time) from each article's content.

Fixes:
  - English cards matched nothing (regex required a path prefix before /articles/)
  - ISO dates leaked onto English cards (2026-09-12 instead of Sep 12, 2026)
  - Chinese reading time was always 5 min (word-based counting on CJK text)
"""
import os, re, glob, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 项目根目录：由脚本所在位置自动推导（_tools/ 的上一级）
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SITE, "_src")
PG = os.path.join(SRC, "pages")

EN_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December']

def read(p):
    return open(p, encoding='utf-8').read()

def split_fm(text):
    m = re.match(r'<!--meta\s*\n(.*?)-->\s*\n', text, re.DOTALL)
    d, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                d[k.strip()] = v.strip()
        body = text[m.end():]
    return d, body

def reading_minutes(body, lang):
    plain = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', body, flags=re.DOTALL)
    plain = re.sub(r'<[^>]+>', ' ', plain)
    if lang == 'zh':
        n = len(re.findall(r'[\u4e00-\u9fff]', plain))
        return max(3, min(15, round(n / 400.0)))
    n = len(re.findall(r"[A-Za-z][A-Za-z'\-]*", plain))
    return max(3, min(15, round(n / 200.0)))

def fmt_date(iso, lang):
    try:
        y, mo, dd = (int(x) for x in iso.split('-'))
    except Exception:
        return iso
    if lang == 'zh':
        return "{}年{}月{}日".format(y, mo, dd)
    return "{} {}, {}".format(EN_MONTHS[mo - 1], dd, y)

def label(date, mins, lang):
    if lang == 'zh':
        return "📅 {} · ⏱ {} 分钟阅读".format(fmt_date(date, lang), mins)
    return "📅 {} · ⏱ {} min read".format(fmt_date(date, lang), mins)

def article_index(lang):
    idx = {}
    for f in glob.glob(os.path.join(PG, lang, "articles", "*.html")):
        meta, body = split_fm(read(f))
        slug = os.path.basename(f)[:-5]
        if meta.get('date'):
            idx[slug] = (meta['date'], reading_minutes(body, lang))
    return idx

def update_home(lang):
    idx = article_index(lang)
    home = os.path.join(PG, lang, "index.html")
    s = read(home)
    stats = {'n': 0}

    def fix(m):
        block = m.group(0)
        # NOTE: no leading slash after href= — English cards are "/articles/x", Chinese "/zh/articles/x"
        h = re.search(r'href="[^"]*?/articles/([a-z0-9\-]+)"', block)
        if not h:
            return block
        slug = h.group(1)
        if slug not in idx:
            return block
        date, mins = idx[slug]
        newlabel = label(date, mins, lang)
        nb, n = re.subn(r'<div class="meta">.*?</div>',
                        '<div class="meta">{}</div>'.format(newlabel), block, flags=re.DOTALL)
        if n:
            stats['n'] += 1
            return nb
        return block

    s2 = re.sub(r'<article class="card">.*?</article>', fix, s, flags=re.DOTALL)
    if s2 != s:
        open(home, 'w', encoding='utf-8').write(s2)
    print("{} homepage: {} cards updated".format(lang, stats['n']))

def main():
    update_home("en")
    update_home("zh")
    for lang, path in [("en", os.path.join(PG, "en", "index.html")),
                       ("zh", os.path.join(PG, "zh", "index.html"))]:
        s = read(path)
        ms = re.findall(r'class="meta">(.*?)</div>', s, re.DOTALL)
        print("  {} ({} cards):".format(lang, len(ms)))
        for m in ms[:4]:
            print("    ", m.strip())
        bad = [m for m in ms if re.match(r'^\d{4}-\d{2}-\d{2}', m.strip())]
        print("    ISO-format leftovers:", len(bad))

if __name__ == "__main__":
    main()
