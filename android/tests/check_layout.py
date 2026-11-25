"""Round-trip desktop layouts through Android's Java model on a development JVM."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from page_state import PageBook

build = ROOT / 'android/build'
build.mkdir(exist_ok=True)
(build / 'tests').mkdir(exist_ok=True)
jar = build / 'json-20250517.jar'
url = 'https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar'
if not jar.exists():
    urllib.request.urlretrieve(url, jar)
expected = urllib.request.urlopen(url + '.sha1', timeout=30).read().decode().strip()
assert hashlib.sha1(jar.read_bytes()).hexdigest() == expected
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
