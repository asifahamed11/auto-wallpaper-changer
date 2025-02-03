import requests
import random
import ctypes
import os
import time
import logging
import sys
import schedule
import threading
from datetime import datetime
from pathlib import Path
import json
import win32com.client
from win32com.shell import shell, shellcon

# Configuration
API_ENDPOINT = "https://www.wallwidgy.me/api/random-wallpapers"
TAGS = ["desktop"]
RESOLUTIONS = ["1080p", "1440p", "4k", "8k"]

DEFAULT_INTERVAL = 3600  # 1 hour

# Setup paths
BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
APPDATA_PATH = Path(os.getenv('APPDATA')) / "WallpaperChanger"
SAVE_DIRECTORY = APPDATA_PATH / "Wallpapers"
LOG_FILE = APPDATA_PATH / "wallpaper_changer.log"
SEEN_WALLPAPERS_FILE = APPDATA_PATH / "seen_wallpapers.json"

# Setup logging
def setup_logging():
    APPDATA_PATH.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_seen_wallpapers():
    if SEEN_WALLPAPERS_FILE.exists():
        with open(SEEN_WALLPAPERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_wallpapers(seen_wallpapers):
    with open(SEEN_WALLPAPERS_FILE, "w") as f:
        json.dump(list(seen_wallpapers), f)

def add_to_startup():
    try:
        startup_folder = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
        shortcut_path = os.path.join(startup_folder, "WallpaperChanger.lnk")

        shell_obj = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell_obj.CreateShortCut(shortcut_path)
        shortcut.TargetPath = str(Path(sys.executable))
        shortcut.Arguments = ""
        shortcut.WorkingDirectory = str(BASE_DIR)
        shortcut.save()

        logging.info("Added to startup successfully")
    except Exception as e:
        logging.error(f"Failed to add to startup: {e}")

def create_save_directory():
    SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)

def cleanup_old_wallpapers():
    wallpapers = sorted(SAVE_DIRECTORY.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True)
    for wallpaper in wallpapers[10:]:
        wallpaper.unlink()
        logging.info(f"Deleted old wallpaper: {wallpaper}")

def fetch_wallpaper(tag, resolution, seen_wallpapers):
    params = {"count": 10, "tag": tag, "resolution": resolution}
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            new_wallpapers = [wp['download_url'] for wp in data if wp['download_url'] not in seen_wallpapers]
            return new_wallpapers[0] if new_wallpapers else None
    except Exception as e:
        logging.error(f"Error fetching wallpaper: {e}")
    return None

def set_wallpaper(image_path):
    try:
        SPI_SETDESKWALLPAPER = 20
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(image_path), 3)
        logging.info(f"Wallpaper set to: {image_path}")
    except Exception as e:
        logging.error(f"Error setting wallpaper: {e}")

def download_wallpaper(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + os.path.basename(url)
        save_path = SAVE_DIRECTORY / filename
        save_path.write_bytes(response.content)
        logging.info(f"Downloaded wallpaper to: {save_path}")
        return save_path
    except Exception as e:
        logging.error(f"Error downloading wallpaper: {e}")
        return None

def change_wallpaper():
    seen_wallpapers = load_seen_wallpapers()
    cleanup_old_wallpapers()
    tag = random.choice(TAGS)
    resolution = random.choice(RESOLUTIONS)
    logging.info(f"Fetching wallpaper with tag '{tag}' and resolution '{resolution}'")
    wallpaper_url = fetch_wallpaper(tag, resolution, seen_wallpapers)
    if wallpaper_url:
        save_path = download_wallpaper(wallpaper_url)
        if save_path:
            set_wallpaper(save_path)
            seen_wallpapers.add(wallpaper_url)
            save_seen_wallpapers(seen_wallpapers)

def schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(10)

def main():
    setup_logging()
    create_save_directory()
    add_to_startup()
    schedule.every(DEFAULT_INTERVAL).seconds.do(change_wallpaper)
    logging.info(f"Wallpaper changer running every {DEFAULT_INTERVAL} seconds")

    # Run scheduling in a separate thread to avoid freezing
    threading.Thread(target=schedule_runner, daemon=True).start()

    # Prevent script from exiting
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
