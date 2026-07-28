#!/usr/bin/env python3
"""Concatenate the whole book into one HTML file and print it to PDF via headless Chromium."""
import re
import subprocess
from pathlib import Path

import markdown

BOOK = Path(__file__).resolve().parent.parent / "book"
SUMMARY = BOOK / "SUMMARY.md"
OUT_HTML = BOOK / "_combined_book.html"
OUT_PDF = BOOK / "mobile-eggbert-bible.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# 1. Determine reading order + part/appendix headings straight from SUMMARY.md
lines = SUMMARY.read_text(encoding="utf-8").splitlines()
sections = []  # list of ("heading", text) or ("file", relpath)
for line in lines:
    m = re.match(r"^## (.+)$", line)
    if m:
        sections.append(("heading", m.group(1)))
        continue
    m = re.match(r"^\|\s*[A-Z0-9]+\s*\|\s*\[[^\]]+\]\(([^)]+)\)\s*\|", line)
    if m:
        sections.append(("file", m.group(1)))

# 2. Build combined markdown
parts = []
parts.append("# Mobile Eggbert Bible\n\n*An in-depth technical book about the source code of "
              "Mobile Eggbert.*\n")

link_re = re.compile(r"\]\(([^)]*?)((?:ch\d+-[a-z0-9-]+)|(?:appendix-[a-z]-[a-z0-9-]+))\.md(#[^)]*)?\)")

for kind, val in sections:
    if kind == "heading":
        parts.append(f"\n\n# {val}\n")
    else:
        fpath = BOOK / val
        text = fpath.read_text(encoding="utf-8")
        text = text.replace("](../images/", "](images/")
        text = link_re.sub(lambda m: f"](#{m.group(2)})", text)
        anchor = Path(val).stem
        parts.append(f'\n\n<div id="{anchor}"></div>\n\n' + text)

combined_md = "\n".join(parts)

# 3. Markdown -> HTML
html_body = markdown.markdown(
    combined_md,
    extensions=["extra", "tables", "fenced_code", "sane_lists", "toc"],
)

css = """
@page { size: A4; margin: 20mm 18mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.45;
       color: #1a1a1a; max-width: 100%; }
h1 { font-size: 20pt; page-break-before: always; margin-top: 0; border-bottom: 2px solid #333;
     padding-bottom: 4px; }
body > h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 15pt; margin-top: 22px; }
h3 { font-size: 12.5pt; }
code, pre { font-family: 'DejaVu Sans Mono', Consolas, monospace; font-size: 8.6pt; }
pre { background: #f4f4f4; padding: 8px; border-radius: 4px; overflow-x: auto;
      white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
code { background: #f0f0f0; padding: 1px 3px; border-radius: 3px; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 4px 7px; text-align: left; vertical-align: top; }
th { background: #e8e8e8; }
img { max-width: 100%; display: block; margin: 10px auto; page-break-inside: avoid; }
blockquote { border-left: 3px solid #999; margin: 8px 0; padding: 2px 14px; color: #444; }
a { color: #1a4d8f; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 18px 0; }
"""

html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Mobile Eggbert Bible</title>
<style>{css}</style></head><body>{html_body}</body></html>"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"Wrote {OUT_HTML} ({len(html):,} bytes)")

# 4. Print to PDF via headless Chromium
subprocess.run([
    CHROME, "--headless", "--disable-gpu", "--no-sandbox",
    "--print-to-pdf=" + str(OUT_PDF),
    "--no-pdf-header-footer",
    "--virtual-time-budget=60000",
    "file://" + str(OUT_HTML),
], check=True)
print(f"Wrote {OUT_PDF}")
