#!/usr/bin/env python3
"""Remove expensive SVG motion while preserving the final visible layout."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: optimize-svg.py INPUT.svg OUTPUT.svg")

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
svg = source.read_text(encoding="utf-8")

# Portrait ASCII lines use animated clip widths. Freeze each clip at its full
# reveal width before removing the 200 per-line SMIL animations.
def freeze_clip(match):
    block = match.group(0)
    width_match = re.search(
        r'<animate\b[^>]*attributeName="width"[^>]*\bto="([^"]+)"',
        block,
        re.IGNORECASE,
    )
    if not width_match:
        return block
    final_width = width_match.group(1)
    block = re.sub(
        r'(<rect\b[^>]*\bwidth=")0("[^>]*>)',
        rf'\g<1>{final_width}\g<2>',
        block,
        count=1,
        flags=re.IGNORECASE,
    )
    return block

svg = re.sub(r'<clipPath\b.*?</clipPath>', freeze_clip, svg, flags=re.IGNORECASE | re.DOTALL)

# Moving neural-network dots have no static coordinates of their own. Keep
# each dot at the beginning of its path, which preserves the composition while
# eliminating 24 independent animateMotion timelines and path calculations.
def freeze_motion(match):
    opening, path_x, path_y, closing = match.groups()
    if not re.search(r'\bcx="', opening, re.IGNORECASE):
        opening = opening.rstrip() + f' cx="{path_x}" cy="{path_y}"'
    return opening + '>' + closing

svg = re.sub(
    r'(<circle\b[^>]*)(?:>\s*)<animateMotion\b[^>]*\bpath="M\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)[^"]*"[^>]*/>\s*(</circle>)',
    freeze_motion,
    svg,
    flags=re.IGNORECASE | re.DOTALL,
)

# Remove SMIL timelines after the affected elements have been made static.
svg = re.sub(
    r'<(?:animateTransform|animateMotion|animate|set)\b[^>]*/>',
    '',
    svg,
    flags=re.IGNORECASE | re.DOTALL,
)

# Strip CSS keyframe blocks and motion declarations as well. The README image
# is intentionally static, so retaining unused keyframes would waste parsing
# and style memory even when animation is overridden.
def remove_keyframe_blocks(source_text):
    pattern = re.compile(r'@(?:-webkit-)?keyframes\b', re.IGNORECASE)
    while True:
        match = pattern.search(source_text)
        if not match:
            return source_text
        brace_start = source_text.find('{', match.end())
        if brace_start < 0:
            return source_text[:match.start()]
        depth = 0
        end = None
        for index in range(brace_start, len(source_text)):
            if source_text[index] == '{':
                depth += 1
            elif source_text[index] == '}':
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            return source_text[:match.start()]
        source_text = source_text[:match.start()] + source_text[end:]

svg = remove_keyframe_blocks(svg)
svg = re.sub(r'\banimation(?:-[\w-]+)?\s*:[^;{}]+;', '', svg, flags=re.IGNORECASE)
svg = re.sub(r'\bwill-change\s*:[^;{}]+;', '', svg, flags=re.IGNORECASE)

# Disable CSS motion globally inside the SVG. This covers the Snake color
# timelines, the marquee's translateX loop, graph reveal effects, neural glow,
# and the remaining decorative CSS animations.
static_style = """
<style id="static-performance-mode">
  * { animation: none !important; transition: none !important; will-change: auto !important; }
  .mq-track-widget_1787002077583 { transform: translateX(0) !important; }
  .c { animation: none !important; }
  .chart-line { stroke-dashoffset: 0 !important; }
</style>
"""
root_match = re.search(r'<svg\b[^>]*>', svg, re.IGNORECASE)
if root_match:
    svg = svg[:root_match.end()] + static_style + svg[root_match.end():]

# A chart line otherwise starts at an off-screen dash offset and relies on its
# animation to reveal itself. Make the final line visible in static mode.
svg = re.sub(r'stroke-dashoffset:\s*5000\s*;', 'stroke-dashoffset: 0;', svg, flags=re.IGNORECASE)
svg = svg.replace('will-change: transform;', '')

if not re.search(r'<svg\b', svg, re.IGNORECASE):
    raise SystemExit("Input is not a valid SVG document")

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(svg, encoding="utf-8")
print(f"Optimized {source} -> {destination} ({len(svg.encode('utf-8'))} bytes)")
