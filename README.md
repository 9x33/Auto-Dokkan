# Dokkan Replay Watcher

A small macOS automation script for Dragon Ball Z Dokkan Battle running through
iPhone Mirroring.

The watcher captures the iPhone Mirroring window, looks for the mission flow
buttons, and clicks:

- `Attempt Again`
- confirmation `OK`
- `Start`

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

Keep the iPhone Mirroring window open and connected. It can be behind other
windows, but the script activates it when it needs to click.

## Notes

The detector is tuned for the visible Dokkan flow we tested: mission results,
stamina confirmation, and start. If the game layout changes, the click regions
or color thresholds may need adjustment.
