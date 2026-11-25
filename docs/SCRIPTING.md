# LPHKscript reference

Adapted from the original LPHK documentation by nimaid.

## What is LPHKscript?
LPHKscript is a simple macro scripting language tailor made for LPHK. Syntax is closer to a shell/batch script than, say, JavaScript.

### Comments
Any line that starts with a dash `-` will be considered a comment, and will be ignored by the syntax validator/script parser. Useful to add notes for yourself or others!

### Scheduling
Only one script runs at a time, and there is a scheduling system for them. If a script is scheduled, it's button will pulse red. If the script is running, the button will flash red quickly. This is true for the 8x8 grid, however, the function keys cannot flash or pulse, as a hardware limitation. These keys will be bright orange for scheduled and bright red for running.

When you press a script button, if there is a script running, it adds the script to the queue. If no scripts are running, the script is added to the queue and the queue execution is started. Tapping a scheduled script's button will unschedule it, and tapping a running scripts button will kill it. If that sounds confusing, load up `user_layouts/examples/all_delays_all_day.lpl` and press a bunch of buttons.

### Headers
Headers are commands that start with `@` and go on the first line of a script. They are used to put the scripting engine into different "modes", allowing you to do some interesting things.

#### The `@ASYNC` Header
There is one exception to the scheduling system. If the script has the `@ASYNC` header, it will run in the background and will not interact with the other scripts. It can still be prematurely killed by tapping the button. If this is used, it must come before any other commands. Only comments and blank lines can come before it.

#### The `@SIMPLE` Header
This is a quick way to bind a controller button to a simple keypress of (argument 1). This has the equivalent code to:
```
@ASYNC
PRESS (argument 1)
WAIT_UNPRESSED
RELEASE (argument 1)
```
If this is used, all other lines in the file must either be blank lines or comments.

### Commands List
Commands follow the format: `COMMAND arg1 arg2 ...`. Scripts are just a text file with newlines separating commands.

#### Utility
* `DELAY`
  * Delays the script for (argument 1) seconds.
* `GOTO_LABEL`
  * Goto label (argument 1).
* `IF_PRESSED_GOTO_LABEL`
  * If the button the script is bound to is pressed, goto label (argument 1).
* `IF_PRESSED_REPEAT_LABEL`
  * If the button the script is bound to is pressed, goto label (argument 1) a maximum of (argument 2) times.
* `IF_UNPRESSED_GOTO_LABEL`
  * If the button the script is bound to is not pressed, goto label (argument 1).
* `IF_UNPRESSED_REPEAT_LABEL`
  * If the button the script is bound to is not pressed, goto label (argument 1) a maximum of (argument 2) times.
* `LABEL`
  * Sets a label named (argument 1) for use with the `*GOTO_LABEL` commands.
* `OPEN`
  * Opens the file or folder (argument 1).
* `REPEAT_LABEL`
  * Goto label (argument 1) a maximum of (argument 2) times.
* `RESET_REPEATS`
  * Reset the counter on all repeats. (no arguments)
* `SOUND`
  * Play a sound named (argument 1) inside the `user_sounds/` folder.
    * Supports `.wav`, `.flac`, and `.ogg` only.
  * If (argument 2) supplied, set volume to (argument 2).
    * Range is 0 to 100
* `SOUND_STOP`
  * Stops all sounds currently playing.
  * If (argument 1) supplied, fading for (argument 1) milliseconds and then stops the sounds.
* `WAIT_UNPRESSED`
  * Waits until the button the script is bound to is unpressed. (no arguments)
* `WEB`
  * Open website (argument 1) in default browser.
* `WEB_NEW`
  * Open website (argument 1) in default browser, try new window.

#### Keypresses
* `PRESS`
  * Presses the key (argument 1).
    * See valid key names below.
* `RELEASE`
  * Releases the key (argument 1).
    * See valid key names below.
* `RELEASE_ALL`
  * Releases all pressed keys, including those pressed by other scripts. (no arguments)
* `STRING`
  * Types whatever text comes after it.
* `TAP`
  * Taps the key (argument 1).
    * See valid key names below.
  * If (argument 2) supplied, tap (argument 2) number of times.
  * If (argument 3) supplied,  delay (argument 3) seconds before releasing each time.

#### Mouse Movement
* `M_LINE`
  * Move the mouse in a line from absolute point (argument 1),(argument 2) to absolute point (argument 3),(argument 4).
  * If (argument 5) supplied, delay (argument 5) milliseconds between each step.
  * If (argument 6) supplied, move (argument 6) pixels per step.
    * If not supplied, assumed to be 1
* `M_LINE_MOVE`
  * Move the mouse cursor in a line (argument 1) horizontally and (argument 2) vertically, relative to current position
  * If (argument 3) supplied, delay (argument 3) milliseconds between each step.
  * If (argument 4) supplied, move (argument 4) pixels per step.
    * If not supplied, assumed to be 1
* `M_LINE_SET`
  * Move the mouse cursor in a line to absolute point (argument 1),(argument 2)
  * If (argument 3) supplied, delay (argument 3) milliseconds between each step.
  * If (argument 4) supplied, move (argument 4) pixels per step.
    * If not supplied, assumed to be 1
* `M_MOVE`
  * Moves the mouse cursor (argument 1) horizontally and (argument 2) vertically, relative to current position.
* `M_RECALL`
  * Sets the mouse position to the last location stored with `M_STORE`.
    * Will not do anything if `M_STORE` has not been called in that script.
* `M_RECALL_LINE`
  * Move the mouse cursor in a line to the last location stored with `M_STORE`.
    * Will not do anything if `M_STORE` has not been called in that script.
  * If (argument 1) supplied, delay (argument 1) milliseconds between each step.
  * If (argument 2) supplied, move (argument 2) pixels per step.
    * If not supplied, assumed to be 1
* `M_SCROLL`
  * Scrolls the mouse vertically by (argument 1).
  * If (argument 2) supplied, scroll horizontally by (argument 2).
* `M_SET`
  * Sets the absolute cursor position to (argument 1) horizontal and (argument 2) vertical.
* `M_STORE`
  * Stores the current mouse position for use with the `M_RECALL*` commands.

### Key Names
For the `PRESS`, `RELEASE`, and `TAP` commands, all single character non-whitespace keys and the following key names are allowed:
* `alt`
* `alt_gr`
* `backspace`
* `caps_lock`
* `cmd`
* `ctrl`
* `delete`
* `down`
* `end`
* `enter`
* `esc`
* `f1` - `f24`
* `home`
* `insert`
* `left`
* `menu`
* `mouse_left`
* `mouse_middle`
* `mouse_right`
* `mute`
* `next_track`
* `num_lock`
* `page_down`
* `page_up`
* `pause`
* `play_pause`
* `prev_track`
* `print_screen`
* `right`
* `scroll_lock`
* `shift`
* `shift_r`
* `space`
* `tab`
* `up`
* `vol_down`
* `vol_up`


## soundtrack controls (0.5.0)

- `SOUND_TRACK "relative filename" [volume] [fade_in_ms] [fade_out_ms]` gives a pad
  a play/pause/resume soundtrack. Defaults are volume 100, no fades. The file is
  relative to user_sounds; quote paths with spaces. Fade times are whole
  milliseconds (0–3600000). Volume is 0–100.
- `SOUND_PAUSE [fade_ms]` pauses all soundtrack pads. With no argument, each
  track uses its own fade-out. The playhead continues during that fade, then
  stays at the point where the channel is actually paused.
- `SOUND_RESUME [fade_ms]` resumes paused soundtrack pads from that position,
  using each track's fade-in unless overridden. It does not start stopped tracks.
- `SOUND_STOP [fade_ms]` keeps its original global stop behavior and also stops
  soundtrack pads. Stopped tracks start from the beginning on the next press.

The original SOUND command still plays overlapping one-shot effects. Global
pause/resume controls apply to soundtrack pads, not these legacy one-shot effects.
Loading a layout or unbinding a soundtrack stops it. Each soundtrack gets its
own channel, so paused tracks are not stolen by new sound effects. Fade updates
run independently of the GUI; state indicators refresh in the main window.

## one-button play/pause (0.5.1)

`SOUND_TRACK "filename" [volume] [play_fade_ms] [stop_fade_ms] [pause_fade_ms]`

The same pad starts, pauses, and resumes a track. Play and resume use the
play_fade_ms value. Pause uses pause_fade_ms. Stop all and the natural end use
stop_fade_ms. All fades are independently configurable in the soundtrack dialog.
The optional pause_fade_ms defaults to stop_fade_ms, preserving older bindings.

The single Play / pause all toolbar button starts all soundtrack bindings if
none are active, pauses playing tracks, and resumes paused tracks. It also
lets you cancel an in-progress pause fade with a second press.


## seeking and pages (0.6.0)

- `SOUND_SKIP seconds [x y]` moves forward or backward relative to the current
  playhead. use a negative number for backward, e.g. `SOUND_SKIP -5`.
- `SOUND_SEEK seconds [x y]` jumps to an absolute position in seconds.
  `SOUND_SEEK 90 0 1` seeks pad 0,1 on the script's page to 01:30.
- without coordinates, seeking applies to all active soundtrack tracks across
  pages. with coordinates, it targets that pad on the script's page. decimal
  seconds are allowed. seeking a paused track keeps it paused. positions are
  clamped to the start/end of the track.
- `PAGE "name"` selects a page by name. `PAGE 2` selects the second page
  (page numbers start at one).
- `PAGE_NEXT` and `PAGE_PREV` cycle through pages, wrapping at either end.

page commands finish the current script; put actions for the new page on its
own pads. switching pages cancels old scripts and releases held input, while
soundtracks keep playing. pages share the 81 simultaneous soundtrack channels.
loading a different layout stops the previous layout's tracks.

the built-in command guide under help includes all commands, with searchable
syntax, explanations, and copyable examples.
