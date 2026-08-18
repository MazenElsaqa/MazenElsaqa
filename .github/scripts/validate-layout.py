#!/usr/bin/env python3
"""Fail the build if intentional full-width widgets drift from the original canvas."""
import json
from pathlib import Path

config = json.loads(Path('gitascii.json').read_text(encoding='utf-8'))
widgets = [w for w in config['widgets'] if w.get('visible')]
full_width_ids = {
    'contribution-snake',
    'godprofile-neural',
    'controlplane-constellation',
}

errors = []
for widget in widgets:
    widget_id = widget.get('widgetId')
    pos = widget.get('position', {})
    size = widget.get('size', {})
    if widget_id in full_width_ids or widget_id == 'divider':
        if pos.get('x') != 0 or size.get('width') != 800:
            errors.append(f'{widget_id}: expected x=0,width=800; got x={pos.get("x")},width={size.get("width")}')

if errors:
    raise SystemExit('\n'.join(errors))

print(f'Validated {len(widgets)} visible widgets; full-width alignment is intact.')
