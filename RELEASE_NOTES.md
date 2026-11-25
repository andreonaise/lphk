## lphk 0.6.0

- inline track monitor below the launchpad, with elapsed / total time.
- actual audio waveform as the progress bar; click it to seek.
- configurable forward/backward skip buttons and SOUND_SKIP / SOUND_SEEK commands.
- multiple saved pages, with page controls and PAGE / PAGE_NEXT / PAGE_PREV commands.
- tracks keep playing across page switches, including separate tracks at the same pad position.
- fullscreen button, f11 / esc shortcuts, and a resizable launchpad grid.
- searchable in-app guide for every script command, with copy/insert examples.
- update button for published releases from andreonaise/lphk, checksum verification,
  restart/install, preserved user files, and a backup of the previous app files.
- existing one-button play/pause, independent fades, and demo mode are kept.

78 automated tests and the windows gui/audio/page checks pass. the packaged
windows app is checked separately. linux/mangowm, audible hardware output,
and real launchpad leds still need on-device testing.
