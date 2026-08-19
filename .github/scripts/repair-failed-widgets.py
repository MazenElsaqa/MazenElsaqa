#!/usr/bin/env python3
"""Repair GitAscii fallback placeholders and external Pokémon image failures."""
from copy import deepcopy
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 4:
    raise SystemExit("usage: repair-failed-widgets.py INPUT.svg FALLBACK.svg OUTPUT.svg")

source_path = Path(sys.argv[1])
fallback_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

source_root = ET.parse(source_path).getroot()
fallback_root = ET.parse(fallback_path).getroot()

widget_ids = [
    "widget-widget_1787002002316",  # ghstats
    "widget-widget_1787002027271",  # activity graph
    "widget-widget_1787002029755",  # contribution snake
    "widget-widget_1787002036075",  # quote
    "widget-widget_1787002149452",  # Pokémon card
]


def by_id(root):
    return {element.attrib.get("id"): element for element in root.iter() if element.attrib.get("id")}


def serialized(element):
    return ET.tostring(element, encoding="unicode")

source_by_id = by_id(source_root)
fallback_by_id = by_id(fallback_root)
parent_by_child = {
    child: parent
    for parent in source_root.iter()
    for child in list(parent)
}

repaired = []
for widget_id in widget_ids:
    current = source_by_id.get(widget_id)
    fallback = fallback_by_id.get(widget_id)
    if current is None or fallback is None:
        continue

    # GitAscii emits a visible error card when an upstream widget endpoint
    # fails. Replace the whole widget with the last-known-good local fragment.
    if "Failed to load widget" in serialized(current):
        parent = parent_by_child.get(current)
        if parent is None:
            raise SystemExit(f"Cannot locate parent for {widget_id}")
        index = list(parent).index(current)
        parent.remove(current)
        parent.insert(index, deepcopy(fallback))
        repaired.append(widget_id)
        continue

    # GitHub/Camo can fail to resolve a remote image nested inside an SVG.
    # The known-good fallback carries the same card image as a data URI.
    if widget_id == "widget-widget_1787002149452":
        current_image = next((e for e in current.iter() if e.tag.rsplit('}', 1)[-1] == 'image'), None)
        fallback_image = next((e for e in fallback.iter() if e.tag.rsplit('}', 1)[-1] == 'image'), None)
        if current_image is not None and fallback_image is not None:
            current_href = current_image.attrib.get("href") or current_image.attrib.get(f"{{{XLINK_NS}}}href")
            fallback_href = fallback_image.attrib.get("href") or fallback_image.attrib.get(f"{{{XLINK_NS}}}href")
            if current_href and current_href.startswith(("http://", "https://")) and fallback_href and fallback_href.startswith("data:"):
                current_image.attrib.pop("href", None)
                current_image.attrib.pop(f"{{{XLINK_NS}}}href", None)
                current_image.set("href", fallback_href)
                if "preserveAspectRatio" in fallback_image.attrib:
                    current_image.set("preserveAspectRatio", fallback_image.attrib["preserveAspectRatio"])
                repaired.append(widget_id + ":embedded-image")

output_path.parent.mkdir(parents=True, exist_ok=True)
ET.ElementTree(source_root).write(output_path, encoding="utf-8", xml_declaration=True)
print(f"Repaired {source_path} -> {output_path}; repaired={','.join(repaired) or 'none'}")
