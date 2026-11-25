## lphk 0.7.0 / android preview 0.2.0

- visual action builder for every script command on desktop and android.
- choose an action and fill in labelled settings instead of writing syntax.
- add, edit, duplicate, reorder, and remove steps in a sequence.
- keyboard shortcut helper with modifier checkboxes and a key selector.
- key, page, audio, and existing-label suggestions; file browsing on desktop
  and audio import on android. fade settings use seconds.
- existing scripts, comments, blank lines, and unknown commands are preserved
  until edited or removed. cancel leaves the original text untouched.
- checks for invalid numbers, incomplete pad targets, misplaced headers,
  standalone hold-key/load-layout bindings, and missing/duplicate labels.
- android desktop-only commands stay editable/exportable without being executed.
- existing text editing and soundtrack settings remain available.

92 desktop unit tests, the visual builder GUI test, and existing windows GUI,
audio, and page checks pass. android checks cover MIDI parsing, layout transfer,
and matching visual-form output for every command. actual phone and launchpad
hardware testing is still pending; linux is built through github actions.
