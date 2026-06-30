#!/bin/zsh
cd "$(dirname "$0")" || exit 1

echo "Starting Auto Dokkan..."
python3 -m pip install -r requirements.txt
python3 dokkan_replay_watcher.py
