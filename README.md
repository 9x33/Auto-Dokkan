# Dokkan Replay Watcher

A small macOS automation script for Dragon Ball Z Dokkan Battle running through
iPhone Mirroring.

The watcher captures the iPhone Mirroring window, looks for the mission flow
buttons, and clicks:

- `Attempt Again`
- confirmation `OK`
- team-select `Start!`

It also includes a small desktop UI that tracks:

- current phase
- missions completed
- clicks sent
- elapsed time
- recent actions and errors

## Requirements

- macOS with iPhone Mirroring
- Python 3
- Pillow
- Screen Recording and Accessibility permissions for the terminal/app running
  the script

## Run

```bash
python3 -m pip install -r requirements.txt
python3 dokkan_replay_watcher.py
```

The UI starts watching automatically. Use the `Stop` button to pause it, or run
with `--manual-start` if you want the window to open without starting.

To run without the UI:

```bash
python3 dokkan_replay_watcher.py --no-ui
```

Keep the iPhone Mirroring window open and connected. It can be behind other
windows, but the script activates it when it needs to click.

## Notes

The detector is tuned for the visible Dokkan flow we tested: mission results,
stamina confirmation, team select, and mission running. If the game layout
changes, the click regions or color thresholds may need adjustment.
