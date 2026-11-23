# lphk

lphk lets you use a novation launchpad as a macro keyboard. each pad can run
a script, press a shortcut, control your music, play a sound, or open something.

this is my fork of [nimaid's lphk](https://github.com/nimaid/LPHK). i've kept
the original scripting language and layout formats, added a dark interface,
and worked on windows, linux, and mangowm support. credit for the original
tool goes to **ella jameson (nimaid)**.

![an example layout in lphk](docs/screenshots/main.png)

the screenshot uses an example layout. there wasn't a launchpad connected when
it was taken.

## getting it running

download the build for your system from this repo's **releases** page, then
extract the whole archive.

- **windows:** open `LPHK.exe`.
- **linux:** open a terminal in the extracted folder and run `./LPHK`.

the release files are named `LPHK-0.4.0-Windows-x86_64.zip` and
`LPHK-0.4.0-Linux-x86_64.tar.gz`. both include python and the app's libraries.
the linux build also bundles the wayland input tools, so you don't need to
install those separately. github's source-code zip needs a development setup.

these builds are for x86_64 windows 10/11 and linux. there aren't macos or arm
builds here. linux builds use ubuntu 22.04 as their glibc baseline; i can't
promise they'll work on every distribution.

you'll still need usb/midi access and the appropriate launchpad driver if your
device needs one. the gui uses x11 or xwayland on linux. file dialogs follow
your desktop's theme.

### cachyos and mangowm

for the prebuilt linux download, run this once from a terminal in your mangowm
session, inside the extracted folder:

```bash
bash install-linux-input.sh
```

then start the app:

```bash
./LPHK
```

the setup script asks for sudo to install the bundled input helper and its
systemd service. it backs up your mangowm config before adding a rule for the
virtual device. it doesn't download python or install application packages.
run the app itself as your normal user.

wayland needs this extra permission step so the helper can send keyboard and
mouse input through `/dev/uinput`. its socket is restricted to your account
with mode `0600`.

use a current mangowm version with `get cursorpos` and `device_rule` support.
lphk talks to mangowm's ipc directly, so `mmsg` isn't required. text entry uses
the virtual keyboard protocol. the wayland backend is intended for mangowm;
other compositors need their own cursor integration.

if your mangowm config lives somewhere else:

```bash
LPHK_MANGO_CONFIG=/path/to/your/config.conf bash install-linux-input.sh
```

you can check the setup with `./LPHK --check-system`. that command doesn't
generate keyboard or mouse input. games, screen locks, pointer grabs, and
desktop bindings can still affect which inputs get through.

## using it

connect your launchpad before opening lphk. if you plug it in afterward, use
**reconnect** or **launchpad > redetect**.

click a pad in **edit** mode, write your script, choose a colour, and press
**bind button**. use **save** to keep the layout.

**move**, **swap**, and **copy** each take two clicks: the source pad, then the
destination. you can also change modes with the original control in the top
right of the grid. new, load, save, and save as are still in the layout menu.
script import/export, validation, colour selection, and unbinding are still
available in the editor.

![the script editor](docs/screenshots/editor.png)

for example, this sends ctrl+c:

```text
PRESS ctrl
TAP c
RELEASE ctrl
```

this toggles media playback:

```text
TAP play_pause
```

and this holds a key for as long as you hold the launchpad button:

```text
@SIMPLE a
```

the full command list is in the [scripting reference](docs/SCRIPTING.md).
you can read it offline from the help menu too.

## your layouts and scripts

layouts use `.lpl`, and individual scripts use `.lps`. the older `.LPHKlayout`
and `.LPHKscript` formats can still be imported.

by default, your files go in `user_layouts`, `user_scripts`, and `user_sounds`
beside the app. keep it in a writable folder. **help > user folder** opens the
location it's actually using.

you can set `LPHK_USER_PATH` to use a different folder. existing `USERPATH`
files also work. examples are copied on first launch without overwriting your
existing examples. a layout at `user_layouts/startup.lpl` loads when you connect.

if you're moving layouts between windows and linux, check any program paths
or os-specific shortcuts in your scripts.

## launchpads

the existing connectors cover classic/mini/s, mkii, mini mk3, launchpad x,
and launchpad pro. pro support still has the original beta limitations; follow
the connection prompts. this fork doesn't add support for unrelated midi
controllers.

## building it yourself

use python 3.11 or 3.12. on windows, run `SETUP.bat`, then `RUN.bat`.
on linux/x11, run `bash SETUP.sh`, then `bash RUN.bash`.

for a cachyos/mangowm source checkout, use `bash SETUP_CACHYOS.sh`. that script
is for development: it uses pacman and downloads python and dependencies.
the prebuilt release's setup script above doesn't do that.

to make a release archive from your development environment:

```bash
python -m pip install -r requirements.txt pyinstaller==6.22.3
python build.py
python release_tools/package_release.py
```

on linux, build the bundled helpers first with
`python release_tools/build_linux_helpers.py`. the build-machine packages are
listed in `.github/workflows/release.yml`. build on the os you're targeting.

### building through github

you can keep the repo private and still use actions. open **actions > build
downloadable apps** and run the workflow to get windows and linux artifacts.
people need access to the private repo to download them.

pushing a tag that matches `VERSION`, such as `v0.4.0`, also creates a draft
release after both builds finish. it includes the app archives, source, and
sha-256 checksums. review the draft before publishing it. publishing a release
in a private repo doesn't make the repo public.

## what has been tested

the windows gui, packaged startup/shutdown, and 34 automated tests have passed.
the gui checks use a fake launchpad and cover the pad modes, script editing,
colour selection, import/export, layout save/load, help, and disconnection.

real launchpad hardware and live mangowm/wayland input still need testing.
a passing build on a linux runner doesn't confirm those work on a real desktop.

if something breaks, include your os, desktop/session type, launchpad model,
and the relevant part of `LPHK.log` from the user folder when reporting it.

## credits

the original lphk was made by **ella jameson (nimaid)**. this is a fork with
changes to the interface, platform support, input handling, and packaging.
it isn't an official novation product or an upstream lphk release.

the original [gpl-3.0 license](LICENSE) is kept. [upstream.md](UPSTREAM.md)
records where the code came from, and [third_party.md](THIRD_PARTY.md) lists the
bundled components. please keep the notices and corresponding source available
when redistributing it.

