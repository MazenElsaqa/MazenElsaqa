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
    "#0d1117": "#FFF8F6",
    "#0D1117": "#FFF8F6",
    "#151c25": "#FFF8F6",
    "#0b0f14": "#FFF8F6",
    "#0B0F14": "#FFF8F6",
    "#080B10": "#FFF8F6",
    "#0B1026": "#FFF8F6",
    "#1e1e2e": "#FFF8F6",
    "#151515": "#FFF8F6",
    "#161b22": "#FFF8F6",
    "#1b1f23": "#FFF8F6",
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

# Recolor only the upper ascii-art widget shown in the reference screenshot.
# Its light-mode text is #1f2937 after the general contrast pass; a deep red
# gives the requested red/white mix while the canvas remains white.
art_start = '<g transform="translate(0, 98)" id="widget-widget_1787001974674">'
art_end = '<g transform="translate(0, 2120)" id="widget-widget_1787013171471_0">'
start = svg.find(art_start)
end = svg.find(art_end, start + len(art_start)) if start >= 0 else -1
if start >= 0 and end > start:
    art = svg[start:end]
    art = art.replace('#1f2937', '#8B1E3F')
    svg = svg[:start] + art + svg[end:]

# Apply warm white to the entire light canvas, not only to card surfaces.
# Insert it after the outermost SVG opening tag so all existing geometry remains
# untouched and the dark-mode asset is unaffected.
root_match = re.search(r'<svg\b[^>]*>', svg, re.IGNORECASE)
if root_match:
    background = '<rect width="100%" height="100%" fill="#FFF8F6"/>\n'
    svg = svg[:root_match.end()] + background + svg[root_match.end():]

# The source SVG is already self-contained. Keep its dimensions and geometry
# untouched; only ensure the output remains an SVG document.
if not re.search(r"<svg\b", svg, re.IGNORECASE):
    raise SystemExit("Input is not a valid SVG document")

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(svg, encoding="utf-8")
print(f"Wrote {destination} ({destination.stat().st_size} bytes)")
