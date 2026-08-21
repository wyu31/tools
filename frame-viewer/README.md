# frame-viewer

A single HTML file for scrubbing through a folder of extracted video frames. No server, no build:
drop it next to the frames and open it in a browser.

## What it does

- Shows one frame at a time with the frame number and a computed timestamp overlaid.
- Slider, prev / next, +-10, play / pause at 2 / 5 / 15 / 30 fps, jump to frame.
- Keyboard: Left / Right step, Shift for 10 at a time, Space plays, Home / End jump to the ends.
- Warns when a frame file is missing instead of silently showing a broken image.

## Usage

1. Extract frames with ffmpeg (any naming works as long as it is prefix + zero-padded number + ext):

   ```bash
   ffmpeg -i clip.mp4 -vf fps=15 -q:v 2 frames/frame_%05d.jpg
   ```

2. Copy `viewer.html` into `frames/`.

3. Open it with the frame set described in the URL query:

   ```
   file:///path/to/frames/viewer.html?total=4485&fps=15
   ```

   All parameters, with defaults:

   | param | default | meaning |
   |---|---|---|
   | `total` | required | number of frames |
   | `fps` | `30` | frame rate used for the timestamp overlay |
   | `prefix` | `frame_` | filename prefix |
   | `pad` | `5` | zero-padding width of the number |
   | `ext` | `jpg` | file extension |
   | `start` | `1` | number of the first file (`0` if ffmpeg was run with `-start_number 0`) |
   | `title` | none | label shown in the header, for example the camera IP |

   Full example: `viewer.html?total=4485&fps=15&prefix=frame_&pad=5&ext=jpg&start=1&title=cam-103`

## Notes

- `file://` works in Safari, Chrome and Firefox because the page only loads sibling images.
  If your browser blocks that, serve the folder with `python3 -m http.server` and open
  `http://localhost:8000/viewer.html?total=...`.
- The timestamp is `(frame - 1) / fps`, which is right for frames extracted at a constant rate.
  For a variable-rate source it is only approximate.
