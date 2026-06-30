#!/usr/bin/env python3
import argparse
import os
import queue
import subprocess
import tempfile
import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime

from PIL import Image


ACTIVATE_SCRIPT = 'tell application "iPhone Mirroring" to activate'
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*getdata.*")


def stamp():
    return datetime.now().strftime("%H:%M:%S")


def window_geometry():
    script = (
        'tell application "System Events" to tell process "iPhone Mirroring" '
        'to get {position, size} of window 1'
    )
    out = subprocess.check_output(["osascript", "-e", script], text=True).strip()
    nums = [int(part.strip()) for part in out.split(",")]
    return nums[0], nums[1], nums[2], nums[3]


def window_id():
    swift = (
        'import CoreGraphics; '
        'let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly); '
        'if let windows = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] { '
        'for w in windows { '
        'if (w[kCGWindowOwnerName as String] as? String) == "iPhone Mirroring" { '
        'print(w[kCGWindowNumber as String] ?? ""); break '
        '} } }'
    )
    out = subprocess.check_output(["swift", "-e", swift], text=True).strip()
    return out.splitlines()[0].strip() if out else ""


def capture_window(path):
    wid = window_id()
    if not wid:
        raise RuntimeError("iPhone Mirroring window not found")
    subprocess.run(
        ["screencapture", "-x", "-l", wid, path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def pixels_for(path, box):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    left, top, right, bottom = box
    crop = im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))
    return list(crop.getdata())


def color_stats(path, box):
    pixels = pixels_for(path, box)
    total = len(pixels)
    if not total:
        return 0, 0, 0, 0

    red = orange = bright = dark = 0
    for r, g, b in pixels:
        if r > 150 and g < 115 and b < 115 and r > g * 1.4 and r > b * 1.4:
            red += 1
        if r > 180 and 80 < g < 185 and b < 95 and r > g * 1.1 and g > b * 1.45:
            orange += 1
        if r > 210 and g > 210 and b > 210:
            bright += 1
        if r < 45 and g < 45 and b < 45:
            dark += 1
    return red / total, orange / total, bright / total, dark / total


def attempt_again_visible(path):
    red, _, bright, _ = color_stats(path, (0.12, 0.80, 0.48, 0.90))
    return red > 0.075, red, bright


def confirm_ok_visible(path):
    _, orange, bright, _ = color_stats(path, (0.50, 0.55, 0.84, 0.66))
    _, _, _, dialog_dark = color_stats(path, (0.12, 0.35, 0.88, 0.72))
    return orange > 0.04 and bright > 0.02 and dialog_dark > 0.35, orange, bright


def friend_request_visible(path):
    _, cancel_orange, cancel_bright, _ = color_stats(path, (0.14, 0.55, 0.48, 0.66))
    _, ok_orange, ok_bright, _ = color_stats(path, (0.50, 0.55, 0.84, 0.66))
    red, _, _, _ = color_stats(path, (0.12, 0.43, 0.32, 0.56))
    _, _, _, dialog_dark = color_stats(path, (0.12, 0.35, 0.88, 0.72))
    visible = (
        red > 0.035
        and cancel_bright > 0.05
        and cancel_orange < 0.02
        and ok_orange > 0.04
        and ok_bright > 0.02
        and dialog_dark > 0.30
    )
    return visible, red, cancel_bright, ok_orange


def team_start_visible(path):
    red, orange, bright, _ = color_stats(path, (0.68, 0.84, 0.91, 0.91))
    return red > 0.09, red, bright


def loading_or_mission_visible(path):
    _, _, _, dark = color_stats(path, (0.05, 0.05, 0.95, 0.95))
    return dark > 0.55


def click_at_screen(x, y):
    subprocess.run(
        ["osascript", "-e", ACTIVATE_SCRIPT],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    swift = (
        "import CoreGraphics; import Foundation; "
        f"let p = CGPoint(x: {x}, y: {y}); "
        "CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, "
        "mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap); "
        "usleep(140000); "
        "CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, "
        "mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap)"
    )
    subprocess.run(
        ["swift", "-e", swift],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def click_window_fraction(fx, fy):
    x, y, width, height = window_geometry()
    click_at_screen(x + int(width * fx), y + int(height * fy))


@dataclass
class WatcherStats:
    running: bool = False
    started_at: float = 0
    phase: str = "Idle"
    missions_completed: int = 0
    clicks_sent: int = 0
    errors: int = 0
    last_action: str = "None"
    recent: list[str] = field(default_factory=list)


class DokkanWatcher:
    def __init__(self, event_queue=None, duration=None):
        self.event_queue = event_queue
        self.duration = duration
        self.stop_event = threading.Event()
        self.stats = WatcherStats()
        self.last_click = 0
        self.result_seen = False

    def emit(self, event, **payload):
        if self.event_queue:
            self.event_queue.put((event, payload))

    def note(self, message):
        line = f"[{stamp()}] {message}"
        print(line, flush=True)
        self.stats.last_action = message
        self.stats.recent.append(line)
        self.stats.recent = self.stats.recent[-60:]
        self.emit("log", line=line)

    def set_phase(self, phase):
        if self.stats.phase != phase:
            self.stats.phase = phase
            self.emit("stats", stats=self.snapshot())

    def snapshot(self):
        return WatcherStats(
            running=self.stats.running,
            started_at=self.stats.started_at,
            phase=self.stats.phase,
            missions_completed=self.stats.missions_completed,
            clicks_sent=self.stats.clicks_sent,
            errors=self.stats.errors,
            last_action=self.stats.last_action,
            recent=list(self.stats.recent),
        )

    def click(self, label, fx, fy, cooldown=2):
        now = time.time()
        if now - self.last_click < cooldown:
            return False
        click_window_fraction(fx, fy)
        self.last_click = now
        self.stats.clicks_sent += 1
        self.note(f"clicked {label}")
        self.emit("stats", stats=self.snapshot())
        return True

    def tick(self, shot):
        capture_window(shot)

        friend, friend_red, cancel_bright, friend_ok_orange = friend_request_visible(shot)
        if friend:
            self.set_phase("Friend request")
            self.click("Friend Request Cancel", 0.32, 0.605, cooldown=2)
            return

        confirm, confirm_orange, _ = confirm_ok_visible(shot)
        if confirm:
            self.set_phase("Confirm stamina")
            self.click("Confirm OK", 0.69, 0.605, cooldown=2)
            return

        attempt, attempt_red, _ = attempt_again_visible(shot)
        if attempt:
            self.set_phase("Mission complete")
            if not self.result_seen:
                self.stats.missions_completed += 1
                self.result_seen = True
                self.note(f"mission complete #{self.stats.missions_completed}")
            self.click("Attempt Again", 0.315, 0.845, cooldown=8)
            return

        team_start, team_red, _ = team_start_visible(shot)
        if team_start:
            self.result_seen = False
            self.set_phase("Team select")
            self.click("Start", 0.79, 0.86, cooldown=8)
            return

        if loading_or_mission_visible(shot):
            self.set_phase("Mission running")
        else:
            self.set_phase("Watching")

        self.note(
            "watching "
            f"attempt_red={attempt_red:.3f} confirm_orange={confirm_orange:.3f} "
            f"friend_red={friend_red:.3f} team_red={team_red:.3f}"
        )

    def run(self):
        self.stats.running = True
        self.stats.started_at = time.time()
        self.set_phase("Starting")
        self.note("watcher started")
        end_at = time.time() + self.duration if self.duration else None

        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "iphone.png")
            while not self.stop_event.is_set():
                if end_at and time.time() >= end_at:
                    break
                try:
                    self.tick(shot)
                except Exception as exc:
                    self.stats.errors += 1
                    self.set_phase("Error")
                    self.note(f"error: {exc}")
                self.emit("stats", stats=self.snapshot())
                time.sleep(2)

        self.stats.running = False
        self.set_phase("Stopped")
        self.note("watcher stopped")
        self.emit("stats", stats=self.snapshot())

    def stop(self):
        self.stop_event.set()


class WatcherApp:
    def __init__(self, auto_start=True):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title("Auto Dokkan")
        self.root.geometry("520x520")
        self.events = queue.Queue()
        self.watcher = None
        self.worker = None

        self.phase = tk.StringVar(value="Idle")
        self.elapsed = tk.StringVar(value="00:00")
        self.completed = tk.StringVar(value="0")
        self.clicks = tk.StringVar(value="0")
        self.errors = tk.StringVar(value="0")
        self.last_action = tk.StringVar(value="None")
        self.running_since = 0

        self.build()
        self.root.after(250, self.drain_events)
        self.root.after(1000, self.update_elapsed)
        if auto_start:
            self.root.after(500, self.start)

    def build(self):
        tk = self.tk
        ttk = self.ttk

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="Auto Dokkan", font=("Helvetica", 22, "bold"))
        title.pack(anchor="w")

        status = ttk.Label(outer, textvariable=self.phase, font=("Helvetica", 15))
        status.pack(anchor="w", pady=(4, 14))

        grid = ttk.Frame(outer)
        grid.pack(fill="x")
        self.stat_row(grid, 0, "Missions", self.completed)
        self.stat_row(grid, 1, "Clicks", self.clicks)
        self.stat_row(grid, 2, "Elapsed", self.elapsed)
        self.stat_row(grid, 3, "Errors", self.errors)

        ttk.Separator(outer).pack(fill="x", pady=14)

        ttk.Label(outer, text="Last Action").pack(anchor="w")
        ttk.Label(outer, textvariable=self.last_action, wraplength=470).pack(anchor="w", pady=(2, 12))

        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log_box = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        scroll.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll.set)

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(14, 0))
        self.start_button = ttk.Button(controls, text="Start", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

    def stat_row(self, parent, col, label, variable):
        frame = self.ttk.Frame(parent, padding=(0, 0, 18, 0))
        frame.grid(row=0, column=col, sticky="w")
        self.ttk.Label(frame, text=label).pack(anchor="w")
        self.ttk.Label(frame, textvariable=variable, font=("Helvetica", 18, "bold")).pack(anchor="w")

    def append_log(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.watcher = DokkanWatcher(event_queue=self.events)
        self.worker = threading.Thread(target=self.watcher.run, daemon=True)
        self.worker.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def stop(self):
        if self.watcher:
            self.watcher.stop()
        self.stop_button.configure(state="disabled")

    def apply_stats(self, stats):
        self.phase.set(stats.phase)
        self.completed.set(str(stats.missions_completed))
        self.clicks.set(str(stats.clicks_sent))
        self.errors.set(str(stats.errors))
        self.last_action.set(stats.last_action)
        self.running_since = stats.started_at if stats.running else 0
        if not stats.running:
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def drain_events(self):
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "log":
                self.append_log(payload["line"])
            elif event == "stats":
                self.apply_stats(payload["stats"])
        self.root.after(250, self.drain_events)

    def update_elapsed(self):
        if self.running_since:
            seconds = int(time.time() - self.running_since)
            self.elapsed.set(f"{seconds // 60:02d}:{seconds % 60:02d}")
        self.root.after(1000, self.update_elapsed)

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Watch iPhone Mirroring and replay Dokkan missions.")
    parser.add_argument("--no-ui", action="store_true", help="run in the terminal without the Tkinter UI")
    parser.add_argument("--manual-start", action="store_true", help="open the UI without starting the watcher")
    parser.add_argument("--minutes", type=int, default=0, help="optional runtime limit for --no-ui mode")
    args = parser.parse_args()

    if args.no_ui:
        duration = args.minutes * 60 if args.minutes else None
        DokkanWatcher(duration=duration).run()
    else:
        WatcherApp(auto_start=not args.manual_start).run()


if __name__ == "__main__":
    main()
