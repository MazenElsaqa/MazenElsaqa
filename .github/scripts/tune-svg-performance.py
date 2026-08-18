#!/usr/bin/env python3
"""Reduce expensive one-shot and redundant motion without disabling the design."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: tune-svg-performance.py INPUT.svg OUTPUT.svg")

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
svg = source.read_text(encoding="utf-8")

# The portrait reveal creates 200 short SMIL timelines. Freeze only those
# clip widths at their final values; all other widget animation is preserved.
def freeze_portrait_clip(match):
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

portrait_clip = re.compile(r'<clipPath\b.*?</clipPath>', re.IGNORECASE | re.DOTALL)
svg = portrait_clip.sub(freeze_portrait_clip, svg)

# Remove only the line-by-line portrait reveal SMIL tags. We intentionally do
# not touch Snake, marquee, globe, chart, or the remaining decorative motion.
svg = re.sub(
    r'<(?:animate|set)\b[^>]*/>',
    '',
    svg,
    flags=re.IGNORECASE | re.DOTALL,
)

# Keep half of the neural dots moving and freeze the other half at their path
# origins. This preserves the animated network impression while reducing the
# number of simultaneous path calculations from 24 to 12.
motion_index = 0
def tune_motion(opening, path_x, path_y, motion, closing):
    global motion_index
    current = motion_index
    motion_index += 1
    if current % 2 == 0:
        return opening + '>' + motion + closing
    if not re.search(r'\bcx="', opening, re.IGNORECASE):
        opening = opening.rstrip() + f' cx="{path_x}" cy="{path_y}"'
    return opening + '>' + closing

svg = re.sub(
    r'(<circle\b[^>]*)(?:>\s*)(<animateMotion\b[^>]*\bpath="M\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)[^"]*"[^>]*/>)(\s*</circle>)',
    lambda match: tune_motion(match.group(1), match.group(3), match.group(4), match.group(2), match.group(5)),
    svg,
    flags=re.IGNORECASE | re.DOTALL,
)

if not re.search(r'<svg\b', svg, re.IGNORECASE):
    raise SystemExit("Input is not a valid SVG document")

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(svg, encoding="utf-8")
print(f"Tuned {source} -> {destination} ({len(svg.encode('utf-8'))} bytes; neural_motion_kept={motion_index // 2})")
