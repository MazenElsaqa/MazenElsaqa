#!/usr/bin/env python3
"""Create a light-mode variant without changing the profile layout or widget geometry."""
from pathlib import Path
import re
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
svg = source.read_text(encoding="utf-8")

# Dark surfaces used by the composite widgets. Keep this deliberately narrow so
# accent colors and ASCII artwork remain unchanged.
surface_colors = {
    "#0d1117": "#ffffff",
    "#0D1117": "#ffffff",
    "#151c25": "#ffffff",
    "#0b0f14": "#ffffff",
    "#0B0F14": "#ffffff",
    "#080B10": "#ffffff",
    "#0B1026": "#ffffff",
    "#1e1e2e": "#ffffff",
    "#151515": "#ffffff",
    "#161b22": "#ffffff",
    "#1b1f23": "#ffffff",
    "#313244": "#e5e7eb",
}

# Light text colors used on dark cards become readable on white cards.
text_colors = {
    "#f0f0f0": "#1f2937",
    "#e5e5e5": "#374151",
    "#E8ECFF": "#1f2937",
    "#cdd6f4": "#374151",
    "#E2E8F0": "#4b5563",
}

for old, new in {**surface_colors, **text_colors}.items():
    svg = svg.replace(old, new)
    svg = svg.replace(old.lower(), new)
    svg = svg.replace(old.upper(), new)

# Make dark structural borders subtle on a white canvas while preserving the
# full-width separators and the original x/y/width/height values.
for old, new in {
    "#252525": "#d1d5db",
    "#2b303a": "#d1d5db",
}.items():
    svg = svg.replace(old, new)
    svg = svg.replace(old.upper(), new)

# Convert white text to dark only when it is attached to text nodes. Do not
# replace white rectangles/backgrounds, which are the intended light surfaces.
svg = re.sub(
    r'(<(?:text|tspan)\b[^>]*fill=")#(?:fff|ffffff)(")',
    r'\1#111827\2',
    svg,
    flags=re.IGNORECASE,
)
svg = re.sub(
    r'(style="[^\"]*?fill\s*:\s*)#(?:fff|ffffff)(?=[;\"])',
    r'\1#111827',
    svg,
    flags=re.IGNORECASE,
)

# Recolor only the portrait widget for light mode. The original artwork uses
# #00c7fc for its ASCII pixels; on a white canvas, a deep red creates the
# requested red/white contrast without changing any other widget.
portrait_start = '<g transform="translate(0, 1246)" id="widget-widget_1787002080734">'
portrait_end = '<g transform="translate(32, 482)" id="widget-widget_1787002149452">'
start = svg.find(portrait_start)
end = svg.find(portrait_end, start + len(portrait_start)) if start >= 0 else -1
if start >= 0 and end > start:
    portrait = svg[start:end]
    portrait = portrait.replace('#00c7fc', '#dc2626')
    portrait = portrait.replace('#00C7FC', '#dc2626')
    svg = svg[:start] + portrait + svg[end:]

# The source SVG is already self-contained. Keep its dimensions and geometry
# untouched; only ensure the output remains an SVG document.
if not re.search(r"<svg\b", svg, re.IGNORECASE):
    raise SystemExit("Input is not a valid SVG document")

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(svg, encoding="utf-8")
print(f"Wrote {destination} ({destination.stat().st_size} bytes)")
