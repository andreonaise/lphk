"""Install a scoped virtual-device rule, backing up the existing config."""
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import mango_ipc

BEGIN = '# BEGIN LPHK WAYLAND'
END = '# END LPHK WAYLAND'
RULE = 'device_rule=name:ydotoold virtual device,kb_layout:us,accel_profile:1,accel_speed:0,natural_scrolling:0,left_handed:0'
BLOCK = f'{BEGIN}\n# Dedicated macro device; physical keyboards and mice keep their settings.\n{RULE}\n{END}\n'


def configure(path):
    path = Path(path)
    original = path.read_text(encoding='utf-8')
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('Malformed LPHK config block; fix it before rerunning setup.')
    if BEGIN in original and original.index(BEGIN) > original.index(END):
        raise ValueError('Malformed LPHK config block; fix it before rerunning setup.')
    pattern = re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?'
    remainder = re.sub(pattern, '', original, flags=re.DOTALL).lstrip('\n')
    updated = BLOCK + '\n' + remainder
    if updated == original:
        return None
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = path.with_name(path.name + '.lphk-backup-' + timestamp)
    shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8', newline='\n')
    return backup


def main():
    root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    path = Path(os.environ.get('LPHK_MANGO_CONFIG', root / 'mango/config.conf')).expanduser()
    if not path.is_file():
        print(f'MangoWM config not found at {path}.')
        print('Set LPHK_MANGO_CONFIG to the config MangoWM actually loads and rerun this script,')
        print('or add this rule yourself:\n' + RULE)
        return 1
    backup = configure(path)
    print(f'MangoWM rule configured in {path}.')
    if backup:
        print(f'Previous config saved as {backup}.')
    try:
        mango_ipc.request('dispatch reload_config')
    except RuntimeError as error:
        print('Reload MangoWM manually to activate the rule:', error)
    return 0


if __name__ == '__main__':
    sys.exit(main())
