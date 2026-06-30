#!/usr/bin/env python3
import os
import subprocess
import tempfile
import time
from datetime import datetime

from PIL import Image


ACTIVATE_SCRIPT = 'tell application "iPhone Mirroring" to activate'


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


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
    return out.splitlines()[0].strip()


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


def button_stats(path, box):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    left, top, right, bottom = box
    crop = im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))
    pixels = list(crop.getdata())
    total = len(pixels)

    red = orange = bright = 0
    for r, g, b in pixels:
        if r > 150 and g < 110 and b < 110 and r > g * 1.45 and r > b * 1.45:
            red += 1
        if r > 180 and 85 < g < 180 and b < 90 and r > g * 1.15 and g > b * 1.5:
            orange += 1
        if r > 210 and g > 210 and b > 210:
            bright += 1

    return red / total, orange / total, bright / total


def mostly_dark(path, box):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    left, top, right, bottom = box
    crop = im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))
    pixels = list(crop.getdata())
    total = len(pixels)
    dark = sum(1 for r, g, b in pixels if r < 45 and g < 45 and b < 45)
    return dark / total


def attempt_again_visible(path):
    red_ratio, _, bright_ratio = button_stats(path, (0.12, 0.80, 0.48, 0.90))
    return red_ratio > 0.075, red_ratio, bright_ratio


def confirm_ok_visible(path):
    _, orange_ratio, bright_ratio = button_stats(path, (0.50, 0.55, 0.84, 0.66))
    dark_ratio = mostly_dark(path, (0.12, 0.35, 0.88, 0.72))
    visible = orange_ratio > 0.04 and bright_ratio > 0.02 and dark_ratio > 0.35
    return visible, orange_ratio, bright_ratio


def start_visible(path):
    _, orange_ratio, bright_ratio = button_stats(path, (0.48, 0.78, 0.90, 0.91))
    replay_red_ratio, _, _ = button_stats(path, (0.12, 0.80, 0.48, 0.90))
    dark_ratio = mostly_dark(path, (0.05, 0.05, 0.95, 0.35))
    visible = (
        replay_red_ratio < 0.04
        and orange_ratio > 0.055
        and bright_ratio > 0.015
        and dark_ratio < 0.8
    )
    return visible, orange_ratio, bright_ratio


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
        "usleep(120000); "
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


def click_attempt_again():
    click_window_fraction(0.315, 0.845)


def click_start():
    click_window_fraction(0.70, 0.845)


def click_confirm_ok():
    click_window_fraction(0.70, 0.605)


def main():
    end_at = time.time() + 60 * 60
    last_click = 0
    log("watcher started")
    with tempfile.TemporaryDirectory() as tmp:
        shot = os.path.join(tmp, "iphone.png")
        while time.time() < end_at:
            try:
                capture_window(shot)
                visible, red_ratio, bright_ratio = attempt_again_visible(shot)
                if visible and time.time() - last_click > 8:
                    click_attempt_again()
                    last_click = time.time()
                    log(f"clicked Attempt Again red={red_ratio:.3f} bright={bright_ratio:.3f}")
                else:
                    confirm, confirm_orange_ratio, confirm_bright_ratio = confirm_ok_visible(shot)
                    if confirm and time.time() - last_click > 2:
                        click_confirm_ok()
                        last_click = time.time()
                        log(
                            "clicked Confirm OK "
                            f"orange={confirm_orange_ratio:.3f} bright={confirm_bright_ratio:.3f}"
                        )
                        time.sleep(1)
                        continue

                    start, orange_ratio, start_bright_ratio = start_visible(shot)
                    if start and time.time() - last_click > 8:
                        click_start()
                        last_click = time.time()
                        log(f"clicked Start orange={orange_ratio:.3f} bright={start_bright_ratio:.3f}")
                    else:
                        log(
                            "watching "
                            f"replay_red={red_ratio:.3f} replay_bright={bright_ratio:.3f} "
                            f"confirm_orange={confirm_orange_ratio:.3f} "
                            f"start_orange={orange_ratio:.3f} start_bright={start_bright_ratio:.3f}"
                        )
            except Exception as exc:
                log(f"error: {exc}")
            time.sleep(3)
    log("watcher finished")


if __name__ == "__main__":
    main()
