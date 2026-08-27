# coord-picker

A tiny Tk tool for reading and naming pixel coordinates on an image. Built for labeling nozzle
positions on CCTV frames of a wafer wet-bench, but it works on any image.


## What it does

- Shows the pixel coordinate and RGB under the cursor, in **original-image pixels** regardless of
  how the image is scaled to fit the window.
- Press **Enter** (or Space, `n`, or right-click) with the cursor on a point, type a name, Enter.
  The point is drawn on the image, listed in the side panel, and written to
  `<image>_coords.txt` next to the image (one `name<TAB>x<TAB>y` per line).
- Click a marker or a list row to select it, **Delete** removes it, `u` undoes the last point.
  Double-click a row (or a selected marker) to rename it.
- With a point selected, the **arrow keys** nudge it by one pixel, **Shift + arrow** by ten.
  Esc deselects.
- With nothing selected, **Left / Right** arrows (or the buttons) step through images in the same folder. Each image has
  its own txt, which is reloaded when you come back.
- **Copy all** copies the image filename followed by every row in the tab-separated format; **cmd+C** copies the selected row
  if there is one, otherwise all. **Copy name** copies the current image's filename.
- Drop an image onto the empty board, or click **+** / `o` to open one.

## Requirements

macOS, Python 3 with a modern Tk (8.6 or 9), Pillow, and optionally tkinterdnd2 for drag-and-drop.

The Python bundled with Xcode (`/usr/bin/python3`) ships Tk 8.5.9, whose canvas renders blank on
current macOS. Use Homebrew instead:

```bash
brew install python-tk@3.13
python3.13 -m pip install --user --break-system-packages pillow tkinterdnd2
```

The shebang points at `/opt/homebrew/bin/python3.13`; edit it if your interpreter lives elsewhere.

## Usage

```bash
chmod +x coord_picker.py
./coord_picker.py                 # empty board, drop or open an image
./coord_picker.py frame.png       # open directly
./coord_picker.py --selftest      # coordinate-mapping and drop-parsing checks
```

Output example (`frame_coords.txt`):

```
Med1 nozzle	316	648
N2 nozzle	456	785
DI nozzle	1288	802
```

The txt is the single source of truth: edit it by hand with the tool closed and the points are
read back on next open.

## Notes

- The window geometry is pinned after launch. Without that, Tk shrinks a maximized window back to
  its requested size whenever a label or list changes.
- Naming uses an entry embedded in the canvas rather than a dialog, because a new toplevel kicks
  macOS out of fullscreen and steals the click.
- No quit key on purpose. Close with the window button or cmd+W; every change is already on disk.
