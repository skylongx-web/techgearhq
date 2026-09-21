"""
Build the static site from _src/.

Usage:  python build.py

Reads:
  _src/templates/shell.html          page skeleton ({{PLACEHOLDERS}})
  _src/templates/header-{lang}.html
  _src/templates/footer-{lang}.html
  _src/pages/**.html                 front-matter + <main> content

Writes:
  <SITE>/*.html, <SITE>/articles/*.html, <SITE>/zh/**   (final pages)
  <SITE>/sitemap.xml
"""
import os, re, glob, io, sys, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 项目根目录：由脚本所在位置自动推导（_tools/ 的上一级）
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SITE, "_src")
SHELL = os.path.join(SRC, "templates", "shell.html")
TODAY = datetime.date.today().isoformat()

DEFAULT_SHELL = """<!DOCTYPE html>
<html lang="{{HTML_LANG}}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESCRIPTION}}">
<link rel="stylesheet" href="/css/style.css">
<link rel="canonical" href="{{CANONICAL}}">
{{HREFLANG}}
{{JSONLD}}
</head>
<body>
{{HEADER}}
{{CONTENT}}
{{FOOTER}}
</body></html>
"""

def read(p, default=""):
    try:
        return open(p, encoding='utf-8').read()
    except Exception:
        return default

def parse_front_matter(text):
    m = re.match(r'<!--meta\s*\n(.*?)-->\s*\n', text, re.DOTALL)
    meta = {}
    body = text
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        body = text[m.end():]
    return meta, body

def rel_to_path(root, abspath):
    r = os.path.relpath(abspath, root).replace('\\', '/')
    return r

EN_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December']

def fmt_date(iso, lang):
    try:
        y, m, d = (int(x) for x in iso.split('-'))
    except Exception:
        return iso
    if lang == 'zh':
        return "{}年{}月{}日".format(y, m, d)
    return "{} {}, {}".format(EN_MONTHS[m - 1], d, y)

def make_jsonld(meta, canonical):
    """Article structured data so Google reads the publish date."""
    title = (meta.get('title', '') or '').replace('"', "'")
    desc = (meta.get('description', '') or '').replace('"', "'")
    d = meta.get('date', TODAY)
    return ('<script type="application/ld+json">'
            '{{"@context":"https://schema.org","@type":"Article",'
            '"headline":"{title}","description":"{desc}",'
            '"datePublished":"{d}","dateModified":"{d}",'
            '"author":{{"@type":"Organization","name":"TechGear HQ"}},'
            '"publisher":{{"@type":"Organization","name":"TechGear HQ"}},'
            '"mainEntityOfPage":{{"@type":"WebPage","@id":"{url}"}}}}'
            '</script>').format(title=title, desc=desc, d=d, url=canonical)

def main():
    shell = read(SHELL) or DEFAULT_SHELL
    if not read(SHELL):
        open(SHELL, 'w', encoding='utf-8').write(DEFAULT_SHELL)
        print("created default shell.html")

    headers = {l: read(os.path.join(SRC, "templates", "header-{}.html".format(l)))
               for l in ('en', 'zh')}
    footers = {l: read(os.path.join(SRC, "templates", "footer-{}.html".format(l)))
               for l in ('en', 'zh')}

    pages = sorted(glob.glob(os.path.join(SRC, "pages", "**", "*.html"), recursive=True))
    built = 0
    urls = []

    for srcf in pages:
        text = read(srcf)
        meta, body = parse_front_matter(text)
        lang = meta.get('lang', 'zh' if '/zh/' in srcf.replace('\\', '/') else 'en')
        rel = rel_to_path(os.path.join(SRC, "pages"), srcf)      # e.g. en/articles/x.html
        # English pages live at the site ROOT, so strip the "en/" prefix
        web_rel = rel[3:] if rel.startswith('en/') else rel      # articles/x.html  |  zh/articles/x.html
        out_path = os.path.join(SITE, web_rel.replace('/', os.sep))

        canonical = meta.get('canonical', '')
        if not canonical:
            canonical = 'https://techgearhq.com/' + (web_rel[:-5] if web_rel.endswith('.html') else web_rel)

        # hreflang pair: en <-> zh for the same slug
        if web_rel.startswith('zh/'):
            en_rel = web_rel[3:]
            zh_rel = web_rel
        else:
            en_rel = web_rel
            zh_rel = 'zh/' + web_rel
        def u(r):
            return 'https://techgearhq.com/' + (r[:-5] if r.endswith('.html') else r)
        hreflang = ""
        if 'articles/' in web_rel:
            hreflang = ('<link rel="alternate" hreflang="en" href="{}">\n'
                        '<link rel="alternate" hreflang="zh-CN" href="{}">').format(u(en_rel), u(zh_rel))

        # --- byline rendered from the front-matter date ---
        if 'articles/' in web_rel and meta.get('date'):
            plain = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', body, flags=re.DOTALL)
            plain = re.sub(r'<[^>]+>', ' ', plain)
            if lang == 'zh':
                mins = max(3, min(15, round(len(re.findall(r'[\u4e00-\u9fff]', plain)) / 400.0)))
            else:
                mins = max(3, min(15, round(len(re.findall(r"[A-Za-z][A-Za-z'\-]*", plain)) / 200.0)))
            byline = ('<div class="byline">{} · {} {} · TechGear HQ</div>'
                      .format(fmt_date(meta['date'], lang), mins,
                              '分钟阅读' if lang == 'zh' else 'min read'))
            if '<div class="byline">' not in body:
                body = re.sub(r'(</h1>)', r'\1\n' + byline, body, count=1)

        jsonld = make_jsonld(meta, canonical) if 'articles/' in web_rel else ''

        html_lang = 'zh-CN' if lang == 'zh' else 'en'
        out = shell
        out = out.replace('{{HTML_LANG}}', html_lang)
        out = out.replace('{{TITLE}}', meta.get('title', ''))
        out = out.replace('{{DESCRIPTION}}', meta.get('description', ''))
        out = out.replace('{{CANONICAL}}', canonical)
        out = out.replace('{{HREFLANG}}', hreflang)
        out = out.replace('{{JSONLD}}', jsonld)
        out = out.replace('{{HEADER}}', headers.get(lang, '').rstrip())
        out = out.replace('{{CONTENT}}', body.rstrip())
        out = out.replace('{{FOOTER}}', footers.get(lang, '').rstrip())

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, 'w', encoding='utf-8').write(out)
        built += 1
        urls.append((canonical, lang, web_rel))
        print("  built", rel)

    print()
    print("Pages built:", built)

    # ---- sitemap ----
    seen = set()
    entries = []
    for u_, lang, rel in urls:
        if u_ in seen:
            continue
        seen.add(u_)
        if rel.endswith('index.html'):
            prio = '1.0'
            freq = 'weekly'
        elif rel.startswith('zh/privacy') or rel == 'en/privacy.html':
            prio = '0.3'
            freq = 'yearly'
        else:
            prio = '0.8' if not rel.startswith('zh/') else '0.7'
            freq = 'monthly'
        entries.append('  <url><loc>{}</loc><lastmod>{}</lastmod>'
                       '<changefreq>{}</changefreq><priority>{}</priority></url>'
                       .format(u_, TODAY, freq, prio))
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + '\n'.join(entries) + '\n</urlset>\n')
    open(os.path.join(SITE, "sitemap.xml"), 'w', encoding='utf-8').write(sm)
    print("sitemap.xml:", len(entries), "URLs")

if __name__ == "__main__":
    main()
