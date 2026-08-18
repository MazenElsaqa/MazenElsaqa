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
# number of simultaneous path calculations from 24 to 12. A marker makes this
# pass idempotent if a generated SVG is accidentally tuned again.
neural_marker = "<!-- neural-motion-tuned -->"
motion_index = 0
if neural_marker not in svg:
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
    root_close = svg.rfind("</svg>")
    if root_close < 0:
        raise SystemExit("Input is not a valid SVG document")
    svg = svg[:root_close] + neural_marker + svg[root_close:]

# Add one low-cost CSS animation to the Pokémon border. The profile is rendered
# by GitHub as an <img>, so :hover is not reliable there; the always-on pulse is
# the visual fallback, while :hover improves the experience when the SVG is
# opened directly. Only one rect is animated, and the existing card image,
# glare, shine, shadow, Snake, marquee, globe, and neural motion are untouched.
card_widget_id = "widget-widget_1787002149452"
card_style_id = "pokemon-card-effects-widget_1787002149452"
card_start = svg.find(f'<g transform="translate(32, 482)" id="{card_widget_id}">')
if card_start >= 0 and card_style_id not in svg:
    border_pattern = re.compile(
        r'(<rect\b[^>]*\bfill="none"[^>]*\bstroke="rgba\(255,255,255,0\.2\)"[^>]*?)(\s*/>)',
        re.IGNORECASE,
    )
    svg, border_count = border_pattern.subn(
        r'\1 class="pokemon-card-border"\2', svg, count=1
    )
    if border_count != 1:
        raise SystemExit("Expected one Pokémon card border rect")
    card_css = f'''\n<style id="{card_style_id}">\n  @keyframes pokemon-card-glow-widget_1787002149452 {{\n    0%, 100% {{\n      stroke: #ff6b9d;\n      stroke-opacity: 0.72;\n      filter: drop-shadow(0 0 2px rgba(255, 107, 157, 0.38));\n    }}\n    25% {{\n      stroke: #ffd166;\n      stroke-opacity: 0.82;\n      filter: drop-shadow(0 0 2px rgba(255, 209, 102, 0.40));\n    }}\n    50% {{\n      stroke: #5eead4;\n      stroke-opacity: 0.78;\n      filter: drop-shadow(0 0 2px rgba(94, 234, 212, 0.38));\n    }}\n    75% {{\n      stroke: #a78bfa;\n      stroke-opacity: 0.84;\n      filter: drop-shadow(0 0 2px rgba(167, 139, 250, 0.42));\n    }}\n  }}\n\n  #{card_widget_id} .pokemon-card-border {{\n    animation: pokemon-card-glow-widget_1787002149452 8s ease-in-out infinite;\n    transform-box: fill-box;\n    transform-origin: center;\n    will-change: filter, opacity;\n  }}\n\n  #{card_widget_id} .pokemon-card-border:hover {{\n    animation-play-state: paused;\n    stroke: #ffffff;\n    stroke-opacity: 1;\n    stroke-width: 2.2;\n    filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.78));\n  }}\n\n  @media (prefers-reduced-motion: reduce) {{\n    #{card_widget_id} .pokemon-card-border {{\n      animation: none;\n      stroke: rgba(255, 255, 255, 0.48);\n      stroke-opacity: 1;\n      filter: none;\n    }}\n  }}\n</style>\n'''
    svg = svg[:svg.rfind("</svg>")] + card_css + svg[svg.rfind("</svg>"):]

if not re.search(r'<svg\b', svg, re.IGNORECASE):
    raise SystemExit("Input is not a valid SVG document")

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(svg, encoding="utf-8")
print(f"Tuned {source} -> {destination} ({len(svg.encode('utf-8'))} bytes; neural_motion_kept={motion_index // 2})")
