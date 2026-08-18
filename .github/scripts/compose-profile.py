#!/usr/bin/env python3
"""Restore the original composite canvas and inject Quote as safe native SVG."""
from html import unescape
from pathlib import Path
import re
import sys
import textwrap
import urllib.request
from xml.sax.saxutils import escape

if len(sys.argv) != 3:
    raise SystemExit("usage: compose-profile.py INPUT_SVG OUTPUT_SVG")

source_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
svg = source_path.read_text(encoding="utf-8")

quote_url = "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=dark"
request = urllib.request.Request(quote_url, headers={"User-Agent": "MazenElsaqa-profile-renderer/1.0"})
with urllib.request.urlopen(request, timeout=30) as response:
    quote_svg = response.read().decode("utf-8", errors="replace")

container_match = re.search(r'<div[^>]*class=["\']container["\'][^>]*>(.*?)</div>', quote_svg, re.IGNORECASE | re.DOTALL)
if not container_match:
    raise SystemExit("Could not locate quote container")

container = container_match.group(1)
paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', container, re.IGNORECASE | re.DOTALL)
quote_text = re.sub(r'<[^>]+>', '', container.split('<p', 1)[0])
quote_text = unescape(re.sub(r'\s+', ' ', quote_text)).strip()
author = unescape(re.sub(r'<[^>]+>', '', paragraphs[0] if paragraphs else "")).strip()
if not quote_text:
    raise SystemExit("Quote text is empty")

# The original widget occupies x=320, y=152, w=464, h=208 and places its
# external card 16px inside that frame. Preserve that geometry exactly.
card_x, card_y, card_w, card_h = 336, 168, 432, 176
lines = textwrap.wrap(quote_text, width=54)[:4]
quote_nodes = [
    f'<rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="0" fill="#151515"/>',
    f'<text x="{card_x + 22}" y="{card_y + 42}" fill="#79ff97" font-family="PT Serif, Georgia, serif" font-size="24">“</text>',
]
for index, line in enumerate(lines):
    y = card_y + 43 + index * 25
    quote_nodes.append(
        f'<text x="{card_x + 42}" y="{y}" fill="#ffffff" font-family="PT Serif, Georgia, serif" font-size="17" font-style="italic">{escape(line)}</text>'
    )
if author:
    author_line = author if author.startswith("-") else f"- {author}"
    quote_nodes.append(
        f'<text x="{card_x + card_w - 18}" y="{card_y + card_h - 18}" fill="#c7c7c7" font-family="PT Serif, Georgia, serif" font-size="13" text-anchor="end" font-style="italic">{escape(author_line)}</text>'
    )

quote_group = '\n  <g id="native-readme-quote">\n    ' + '\n    '.join(quote_nodes) + '\n  </g>\n'
if 'id="native-readme-quote"' in svg:
    svg = re.sub(r'\s*<g id="native-readme-quote">.*?</g>\s*', '\n', svg, flags=re.DOTALL)
root_close = svg.rfind('</svg>')
if root_close < 0:
    raise SystemExit('Could not locate root SVG closing tag')
svg = svg[:root_close] + quote_group + svg[root_close:]

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(svg, encoding="utf-8")
print(f"Wrote {output_path} ({output_path.stat().st_size} bytes) with quote: {quote_text}")
