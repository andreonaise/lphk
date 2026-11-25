"""Small non-secret preferences file stored with the user's layouts."""
import json
import math
import sys
from pathlib import Path

DEFAULTS = {'update_repository': 'andreonaise/lphk', 'skip_seconds': 5.0, 'fullscreen': False}


def load(folder):
    values = DEFAULTS.copy()
    try:
        metadata = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'UPDATE_REPOSITORY'
        values['update_repository'] = metadata.read_text().strip()
    except OSError:
        pass
    try:
        data = json.loads((Path(folder) / 'settings.json').read_text(encoding='utf-8'))
        values.update({key: data[key] for key in DEFAULTS if key in data})
        skip = float(values['skip_seconds'])
        if not math.isfinite(skip) or not 0 < skip <= 3600:
            values['skip_seconds'] = DEFAULTS['skip_seconds']
    except (OSError, ValueError, TypeError):
        pass
    return values


def save(folder, values):
    destination = Path(folder) / 'settings.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({key: values.get(key, default) for key, default in DEFAULTS.items()}, indent=2), encoding='utf-8')
    temporary.replace(destination)
