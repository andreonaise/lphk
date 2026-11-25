"""Keep the offline Android command guide and demo aligned with desktop LPHK."""
import ast
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import script_builder
module = ast.parse((ROOT.parent / 'command_guide.py').read_text(encoding='utf-8'))
catalog = ast.literal_eval(next(node.value for node in module.body if isinstance(node, ast.Assign)
                                and any(getattr(target, 'id', None) == 'COMMANDS' for target in node.targets)))
(ROOT / 'assets').mkdir(exist_ok=True)
(ROOT / 'assets/commands.json').write_text(json.dumps([
    dict(name=name, category=data[0], syntax=data[1], description=data[2], example=data[3])
    for name, data in catalog.items()], ensure_ascii=False), encoding='utf-8', newline='\n')
shutil.copy2(ROOT.parent / 'user_sounds/examples/demo_track.wav', ROOT / 'assets/demo_track.wav')
(ROOT / 'assets/forms.json').write_text(json.dumps(dict(keys=script_builder.KEYS, commands=[
    dict(command=name, title=entry[0], fields=entry[1],
         description=script_builder.form_description(catalog[name][2]) if name in catalog else 'A note for yourself; it does not run anything.')
    for name, entry in script_builder.FORMS.items()]), ensure_ascii=False), encoding='utf-8', newline='\n')
