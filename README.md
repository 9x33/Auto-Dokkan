# Dokkan Replay Watcher

A small macOS automation script for Dragon Ball Z Dokkan Battle running through
iPhone Mirroring.

[![Download Auto Dokkan UI](https://img.shields.io/badge/Download%20Auto%20Dokkan%20UI-main.zip-2ea44f?style=for-the-badge)](https://github.com/9x33/Auto-Dokkan/archive/refs/heads/main.zip)

Download the UI with the button above, unzip it, then double-click
`Auto Dokkan.command` to open the progress window.

The watcher captures the iPhone Mirroring window, looks for the mission flow
buttons, and clicks:

- `Attempt Again`
- confirmation `OK`
- friend request `Cancel`
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

## Open The UI

Use the download button above, unzip the file, then double-click
`Auto Dokkan.command`.

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
stamina confirmation, friend request prompts, team select, and mission running.
If the game layout changes, the click regions or color thresholds may need
adjustment.
