"""Round-trip desktop layouts through Android's Java model on a development JVM."""
from pathlib import Path
import hashlib
import ast
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from page_state import PageBook
import script_builder

build = ROOT / 'android/build'
build.mkdir(exist_ok=True)
(build / 'tests').mkdir(exist_ok=True)
jar = build / 'json-20250517.jar'
url = 'https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar'
if not jar.exists():
    urllib.request.urlretrieve(url, jar)
assert hashlib.sha256(jar.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
book = PageBook()
book.rename('Desktop')
book.current['buttons'][4][4]['text'] = 'PRESS ctrl\nTAP c\nRELEASE ctrl'
book.activate(book.add('Music'))
book.current['buttons'][0][1] = dict(text='SOUND_TRACK "imports/my song.wav" 80 1500 2000 500', color=[85, 153, 119])
fixture = build / 'desktop-layout.lpl'
fixture.write_text(json.dumps(book.to_layout()), encoding='utf-8')
java = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else Path(shutil.which('java')).parent
suffix = '.exe' if os.name == 'nt' else ''
source = ROOT / 'android/src/io/github/andreonaise/lphk/LayoutData.java'
subprocess.run([str(java / ('javac' + suffix)), '--release', '8', '-cp', str(jar), '-d', str(build / 'tests'),
                str(source), str(ROOT / 'android/tests/LayoutTest.java')], check=True)
result = build / 'android-layout.lpl'
subprocess.run([str(java / ('java' + suffix)), '-cp', os.pathsep.join([str(build / 'tests'), str(jar)]),
                'io.github.andreonaise.lphk.LayoutTest', str(fixture), str(result)], check=True)
actual = PageBook()
actual.load(json.loads(result.read_text(encoding='utf-8')))
assert actual.to_layout() == book.to_layout()
print('Desktop -> Android -> desktop layouts match exactly, including active page, script text and RGB.')
module = ast.parse((ROOT / 'command_guide.py').read_text(encoding='utf-8'))
catalog = ast.literal_eval(next(n.value for n in module.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'COMMANDS' for t in n.targets)))
vectors = []
for command, entry in catalog.items():
    line = next(line for line in entry[3].splitlines() if line.split()[0] == command)
    _, values = script_builder.parse(line)
    vectors.append(dict(command=command, values=values, script=script_builder.build(command, values)))
for command, values in [('-',dict(text='comment with spaces')), ('TAP',dict(key='space',count='',hold='.2')),
                        ('PAGE',dict(page='My music')), ('STRING',dict(text='hello world')), ('OPEN',dict(path='C:\\my files\\test.txt')),
                        ('SOUND_PAUSE',dict(fade='')), ('SOUND_PAUSE',dict(fade='.125')), ('SOUND_SKIP',dict(seconds='-2.5',x='',y=''))]:
    vectors.append(dict(command=command, values=values, script=script_builder.build(command, values)))
vectors_path = build / 'form-vectors.json'
vectors_path.write_text(json.dumps(vectors),encoding='utf-8')
java_sources = [ROOT / 'android/src/io/github/andreonaise/lphk' / name for name in ('ActionForms.java','ScriptSyntax.java')]
subprocess.run([str(java / ('javac' + suffix)), '--release', '8', '-cp', str(jar), '-d', str(build / 'tests'),
                *map(str,java_sources), str(ROOT / 'android/tests/FormTest.java')],check=True)
subprocess.run([str(java / ('java' + suffix)), '-cp', os.pathsep.join([str(build / 'tests'), str(jar)]),
                'io.github.andreonaise.lphk.FormTest', str(ROOT / 'android/assets/forms.json'),str(vectors_path)],check=True)
