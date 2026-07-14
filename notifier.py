import os
import time
import json
import requests
import numpy as np
import cv2
from dotenv import load_dotenv
from mss import mss


def load_config(path="config.json"):
    load_dotenv()
    cfg = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token:
        cfg["telegram_token"] = token
    if chat_id:
        cfg["telegram_chat_id"] = chat_id
    return cfg


def validate_config(cfg):
    token = str(cfg.get("telegram_token", "")).strip()
    chat_id = str(cfg.get("telegram_chat_id", "")).strip()
    if not token:
        raise ValueError("telegram_token is missing in config.json")
    if not chat_id:
        raise ValueError("telegram_chat_id is missing in config.json")
    if chat_id.lower().endswith("_bot"):
        print("Warning: telegram_chat_id looks like a bot username. Use your numeric chat ID or channel username, not a bot username.")
    return token, chat_id


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    max_attempts = 3
    backoff = 1
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Sending Telegram message (attempt {attempt})")
            resp = requests.post(url, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                print(f"Telegram message sent (message_id={msg_id})")
                return True
            print("Telegram API returned error:", data)
        except requests.RequestException as e:
            details = None
            try:
                details = resp.text
            except Exception:
                details = str(e)
            print(f"Failed to send Telegram message (attempt {attempt}): {details}")
        time.sleep(backoff)
        backoff *= 2
    return False


def count_red_pixels(img_bgr):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower1 = np.array([0, 60, 50])
    upper1 = np.array([15, 255, 255])
    lower2 = np.array([165, 60, 50])
    upper2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask_hsv = cv2.bitwise_or(mask1, mask2)

    b, g, r = cv2.split(img_bgr)
    bgr_mask = ((r.astype(int) > 120) & (r.astype(int) > g.astype(int) + 40) & (r.astype(int) > b.astype(int) + 40)).astype("uint8") * 255

    mask = cv2.bitwise_or(mask_hsv, bgr_mask)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
    return int(cv2.countNonZero(mask)), mask


def monitor_loop(cfg, token, chat_id, message_text=None, log_fn=print, stop_event=None):
    interval = float(cfg.get("check_interval", 2))
    monitor = cfg.get("monitor")
    pixel_threshold = int(cfg.get("pixel_threshold", 1))
    min_red_fraction = cfg.get("min_red_fraction")
    if min_red_fraction is not None:
        min_red_fraction = float(min_red_fraction)
        if min_red_fraction <= 0.0:
            min_red_fraction = None
    notify_on_startup = bool(cfg.get("notify_on_startup", True))

    sct = mss()
    region = {k: int(monitor[k]) for k in ("left", "top", "width", "height")} if monitor else None
    img = np.array(sct.grab(region))[:, :, :3]
    red_count, _mask = count_red_pixels(img)
    area = img.shape[0] * img.shape[1]
    red_fraction = red_count / area if area > 0 else 0.0

    if notify_on_startup:
        last_seen = False
        log_fn(f"Starting monitor loop. notify_on_startup=True; initial badge={red_count >= pixel_threshold}, red_count={red_count}, red_fraction={red_fraction:.4f}")
    else:
        last_seen = (red_count >= pixel_threshold)
        if min_red_fraction is not None:
            last_seen = last_seen or (red_fraction >= min_red_fraction)
        if last_seen:
            log_fn(f"Starting monitor loop. Badge already present at startup; waiting for disappearance before notifying. red_count={red_count}, red_fraction={red_fraction:.4f}")
        else:
            log_fn(f"Starting monitor loop. No badge present at startup. red_count={red_count}, red_fraction={red_fraction:.4f}")

    def sleep_interval():
        if stop_event is not None:
            return stop_event.wait(interval)
        time.sleep(interval)
        return False

    try:
        while True:
            img = np.array(sct.grab(region))[:, :, :3]
            red_count, _mask = count_red_pixels(img)
            area = img.shape[0] * img.shape[1]
            red_fraction = red_count / area if area > 0 else 0.0
            is_red = (red_count >= pixel_threshold)
            if min_red_fraction is not None:
                is_red = is_red or (red_fraction >= min_red_fraction)

            log_fn(f"scan: red_count={red_count}, red_fraction={red_fraction:.4f}, is_red={is_red}, last_seen={last_seen}")

            if is_red and not last_seen:
                log_fn("Detected red badge and will send notification.")
                if token and chat_id:
                    ok = send_telegram(token, chat_id, message_text or "New message detected on Freelancer")
                    if not ok:
                        log_fn("Notification failed after retries; will resume monitoring and try again on next badge.")
                else:
                    log_fn("Telegram token/chat_id not set in config.json")
                last_seen = True

            if not is_red and last_seen:
                log_fn("Badge disappeared; ready to detect the next new message.")
                last_seen = False

            if sleep_interval():
                break
    except KeyboardInterrupt:
        log_fn("Stopped by user")
    finally:
        log_fn("Monitor stopped.")
