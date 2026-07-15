# Dokkan Replay Watcher

A small macOS automation script for Dragon Ball Z Dokkan Battle running through
iPhone Mirroring.

[![Download Auto Dokkan App](https://img.shields.io/badge/Download%20Auto%20Dokkan%20App-.zip-2ea44f?style=for-the-badge)](https://github.com/9x33/Auto-Dokkan/raw/main/dist/AutoDokkan.zip)

Download the app with the button above, unzip it, then drag `Auto Dokkan.app`
into `Applications`.

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
- Screen Recording and Accessibility permissions for Auto Dokkan

## Open The App

Use the download button above, unzip it, drag `Auto Dokkan.app` into
`Applications`, then open it from Applications.

The UI starts watching automatically. Use the `Stop` button to pause it and
`Start` to resume.

macOS may ask for permissions the first time the app runs:

- Screen Recording, so it can inspect the iPhone Mirroring window
- Accessibility, so it can click buttons through iPhone Mirroring
- Automation, so it can activate iPhone Mirroring when a click is needed

Keep the iPhone Mirroring window open and connected. It can be behind other
windows, but the app activates it when it needs to click. If iPhone Mirroring is
closed or the phone disconnects, Auto Dokkan will wait until the window exists
again.

Auto Dokkan keeps running while its own window is behind other apps or minimized.
The iPhone Mirroring window can also be behind other apps; it does not need to
stay in front except for the brief moment when Auto Dokkan sends a click.

## Notes

The detector is tuned for the visible Dokkan flow we tested: mission results,
stamina confirmation, friend request prompts, team select, and mission running.
If the game layout changes, the click regions or color thresholds may need
adjustment.
