# lphk for android

this is the first android version, focused on a touchscreen launchpad and
editing layouts for a physical launchpad mini. it runs on android 8.0 or newer.
the apk includes the app and demo audio; you don't need python on your phone.

## installing

copy `LPHK-Android-0.2.0.apk` to the phone and open it. android may ask you to
allow installations from the app you used to open the file. install lphk,
then open it normally.

the provided apk is a preview signed with a development key. its build and
signature were verified, and the midi/parser checks passed. it has not been
run on a phone or tested with a physical launchpad in this environment.

## touchscreen pads

the included demo has two track pads and a stop pad. choose **play pads**,
then tap a green or blue pad to start, pause, or resume its track. you can
press several touchscreen pads at once. stop resets playback.

switch back to **edit pads** and tap a pad to change its script and colour.
**import audio / soundtrack** copies an audio file into the app. **soundtrack
settings** lets you set volume and separate play/resume, pause, and stop/end
fades. apply the settings, then save the pad.

you can now use **build actions…** for the whole pad script. add an action,
choose it from the list, fill in its settings, and arrange actions in order.
edit, copy, remove, move up/down, and a keyboard-shortcut helper are included.
apply the sequence to the pad editor, then save the pad. the forms cover all
desktop commands too; those are marked desktop only and remain exportable.
you don't need to write command syntax. the existing text editor is kept.

the monitor below the grid shows the selected track, elapsed/total time,
and its decoded waveform when the audio decoder supports it. tap the waveform
to seek, or set **skip (s)** for the back/forward buttons. seeking a paused
track keeps it paused. large files may take longer to show their waveform.

audio pauses when lphk leaves the foreground, including when a file picker
opens. return to the app and resume it. this version doesn't provide a
background audio service or lock-screen controls.

## physical launchpad mini

connect the mini to the phone with a usb otg adapter. the phone must support
usb host and android midi. a powered usb hub may be needed if the phone
cannot provide enough power.

tap **connect**, select the device, and choose its model:

- **launchpad mini / mini mk2 / classic:** the original red/green model.
- **launchpad mini mk3:** the rgb model. the app enters programmer mode and
  returns to live mode when disconnected normally.

if several midi ports appear, choose the midi ports rather than daw ports.
in edit mode, pressing a real pad opens that pad's editor. in play mode,
the real pads trigger the same assignments as the touchscreen. playing pads
are green and paused pads are amber. the original mini only has red/green
leds, so other colours are approximated.

the scripts run on the phone while the app and launchpad are connected.
they are not installed into the launchpad as standalone programs. this
version targets the mini family, not launchpad pro or other controllers.

## pages and desktop layouts

the page selector and arrows switch between pages. **+** adds one; rename
and delete are in the menu. tracks continue when you switch pages.
saved pad edits and page changes are kept automatically in the app's storage.

**menu > import layout / bundle** opens desktop json `.lpl` layouts,
including multi-page layouts. old non-json `.LPHKlayout` files need to be
converted with desktop lphk first.

**export layout (.lpl)** saves a desktop-compatible layout. **export layout +
audio (.zip)** includes `layout.lpl` and `user_sounds/`, including your imported
audio. on the desktop, extract that bundle, merge `user_sounds/` into the
desktop app's user sound folder, and load `layout.lpl`. use the user folder
shown in desktop lphk's help menu.

you can import that same bundle back on android. a desktop-made bundle must
have `layout.lpl` at its root and any audio under `user_sounds/`, keeping the
relative paths used in scripts. audio isn't embedded in a plain `.lpl` file.
an import refuses to replace an existing sound with different content at the
same path; rename the conflicting file and update its script first.

android and desktop lphk read the same pad script text and rgb colours.
keyboard/mouse and external-program commands are retained in layouts and can
be edited and exported for desktop use. attempting to run them here reports
that they require desktop lphk; they aren't silently ignored.

the command guide marks each command as android or desktop only. audio,
delay, held-pad conditions, labels/repeats, page changes, and http/https web
links can run here. this version doesn't run desktop keyboard or mouse input,
external programs, `@SIMPLE`, or `@LOAD_LAYOUT`, and doesn't connect remotely
to a computer. it doesn't need root or an accessibility service.

## building on github

upload the repository files, including `android/` and `.github/`, to the repo.
open **actions > build android apk > run workflow**. when it finishes, open
the run and download the `LPHK-Android-0.2.0` artifact. extract it to get the apk.
the desktop windows/linux workflow remains separate.

the workflow builds a development-signed apk unless release signing secrets
are configured. a fresh development signing key is created on each github
run, so those builds cannot update one another in place. export your layout
bundle before uninstalling a differently signed build, since uninstalling
removes the app's private layouts and audio.

for consistent releases, create and keep a private signing keystore and set
these github actions secrets:

- `ANDROID_KEYSTORE_BASE64`: the base64-encoded keystore.
- `ANDROID_KEYSTORE_PASSWORD`: its store and key password (use the same for both).
- `ANDROID_KEY_ALIAS`: its key alias.

use the same private key for future releases. don't upload the keystore to
the repo. the supplied local preview's development key is not in this kit.

## building locally

install jdk 17 and the official android sdk with `platforms;android-35` and
`build-tools;35.0.0`. set `ANDROID_SDK_ROOT` to the sdk folder and, if needed,
`JAVA_HOME` to the jdk. with python 3.11 or newer:

```text
python android/build_apk.py
```

the script compiles the java source, runs the protocol/parser checks, builds
the dex/resources, signs the apk, and verifies its signature. the result is
`android/build/LPHK-Android-0.2.0.apk`. there are no third-party app libraries
or gradle dependencies. build output and local signing keys are excluded
from the source export.

`python android/tests/check_layout.py` additionally checks desktop → android →
desktop layout compatibility. that development test downloads JSON-java from
maven central for use on the development JVM; it is not bundled in the apk.

optional environment variables for a release key are `LPHK_KEYSTORE`,
`LPHK_KEYSTORE_PASSWORD`, and `LPHK_KEY_ALIAS`. the build refuses to generate
a replacement when an explicitly configured release keystore is missing.

## credits and license

based on ella jameson (nimaid)'s lphk, under the repository's gpl-3.0 license.
the mini midi coordinate/led conventions follow the existing desktop
`launchpad_py` integration; the android implementation uses android's midi
api directly. no novation drivers or firmware are bundled.

android api references: [midi](https://developer.android.com/reference/android/media/midi/MidiManager),
[usb host](https://developer.android.com/develop/connectivity/usb/host), and
[apk signing](https://developer.android.com/tools/apksigner).
