"""Keep the offline Android command guide and demo aligned with desktop LPHK."""
import ast
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
module = ast.parse((ROOT.parent / 'command_guide.py').read_text(encoding='utf-8'))
catalog = ast.literal_eval(next(node.value for node in module.body if isinstance(node, ast.Assign)
                                and any(getattr(target, 'id', None) == 'COMMANDS' for target in node.targets)))
(ROOT / 'assets').mkdir(exist_ok=True)
(ROOT / 'assets/commands.json').write_text(json.dumps([
    dict(name=name, category=data[0], syntax=data[1], description=data[2], example=data[3])
    for name, data in catalog.items()], ensure_ascii=False), encoding='utf-8', newline='\n')
shutil.copy2(ROOT.parent / 'user_sounds/examples/demo_track.wav', ROOT / 'assets/demo_track.wav')
