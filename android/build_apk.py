"""Build a signed APK with the standard Android SDK and JDK 17; no Gradle needed."""
from pathlib import Path
import os
import shutil
import subprocess
import zipfile
import runpy

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
SDK = Path(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME') or ROOT.parents[1] / 'android-sdk')
JAVA = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else Path(shutil.which('java')).parent
TOOLS = SDK / 'build-tools/35.0.0'
JAR = SDK / 'platforms/android-35/android.jar'
EXE = '.exe' if os.name == 'nt' else ''
for folder in ('classes', 'dex', 'generated', 'tests'):
    target = (BUILD / folder).resolve()
    assert target.is_relative_to(BUILD.resolve())
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
runpy.run_path(str(ROOT / 'prepare_assets.py'))


def run(*arguments):
    subprocess.run([str(a) for a in arguments], check=True, cwd=ROOT)


def java_tool(name):
    return JAVA / (name + EXE)


# Independent protocol/parser regression tests don't need a phone or emulator.
package = ROOT / 'src/io/github/andreonaise/lphk'
run(java_tool('javac'), '--release', '8', '-d', BUILD / 'tests', package / 'MidiProtocol.java',
    package / 'ScriptSyntax.java', ROOT / 'tests/ProtocolTest.java')
run(java_tool('java'), '-cp', BUILD / 'tests', 'io.github.andreonaise.lphk.ProtocolTest')
run(TOOLS / ('aapt2' + EXE), 'compile', '--dir', ROOT / 'res', '-o', BUILD / 'resources.zip')
run(TOOLS / ('aapt2' + EXE), 'link', '-o', BUILD / 'resources.apk', '-I', JAR,
    '--manifest', ROOT / 'AndroidManifest.xml', '-A', ROOT / 'assets', '--java', BUILD / 'generated', BUILD / 'resources.zip')
sources = sorted((ROOT / 'src').rglob('*.java')) + sorted((BUILD / 'generated').rglob('*.java'))
run(java_tool('javac'), '--release', '8', '-encoding', 'UTF-8', '-classpath', JAR,
    '-d', BUILD / 'classes', *sources)
class_files = sorted((BUILD / 'classes').rglob('*.class'))
run(java_tool('java'), '-cp', TOOLS / 'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26',
    '--lib', JAR, '--output', BUILD / 'dex', *class_files)
shutil.copy2(BUILD / 'resources.apk', BUILD / 'unsigned.apk')
with zipfile.ZipFile(BUILD / 'unsigned.apk', 'a', zipfile.ZIP_DEFLATED) as z:
    for dex in (BUILD / 'dex').glob('*.dex'):
        z.write(dex, dex.name)
run(TOOLS / ('zipalign' + EXE), '-f', '4', BUILD / 'unsigned.apk', BUILD / 'aligned.apk')
key = Path(os.environ.get('LPHK_KEYSTORE', ROOT / '.keys/debug.keystore')).resolve()
key.parent.mkdir(parents=True, exist_ok=True)
password = os.environ.get('LPHK_KEYSTORE_PASSWORD', 'android')
alias = os.environ.get('LPHK_KEY_ALIAS', 'androiddebugkey')
if not key.exists():
    if os.environ.get('LPHK_KEYSTORE'):
        raise SystemExit('LPHK_KEYSTORE does not exist; refusing to generate a replacement release key.')
    run(java_tool('keytool'), '-genkeypair', '-keystore', key, '-storepass', 'android', '-keypass', 'android',
        '-alias', alias, '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000',
        '-dname', 'CN=Android Debug,O=Android,C=US')
# Pass a keystore password through the environment rather than the process arguments.
os.environ['LPHK_SIGN_PASSWORD'] = password
destination = BUILD / 'LPHK-Android-0.1.0.apk'
run(java_tool('java'), '-jar', TOOLS / 'lib/apksigner.jar', 'sign', '--ks', key,
    '--ks-key-alias', alias, '--ks-pass', 'env:LPHK_SIGN_PASSWORD', '--key-pass', 'env:LPHK_SIGN_PASSWORD',
    '--out', destination, BUILD / 'aligned.apk')
run(java_tool('java'), '-jar', TOOLS / 'lib/apksigner.jar', 'verify', '--verbose', destination)
run(TOOLS / ('aapt2' + EXE), 'dump', 'badging', destination)
print(destination)
