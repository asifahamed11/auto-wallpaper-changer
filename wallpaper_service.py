import requests
import random
import ctypes
import os
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
import winreg
import win32com.client
import pythoncom
from win32com.shell import shell, shellcon

# Configuration
API_ENDPOINT = "https://www.wallwidgy.me/api/random-wallpapers"
TAGS = ["desktop"]
RESOLUTIONS = ["1080p", "1440p", "4k", "8k"]
CHANGE_INTERVAL = 3600  #1 hour
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Setup paths
APPDATA_PATH = Path(os.getenv('APPDATA')) / "WallpaperChanger"
SAVE_DIRECTORY = APPDATA_PATH / "Wallpapers"
LOG_FILE = APPDATA_PATH / "wallpaper_changer.log"

# Setup logging
def setup_logging():
    APPDATA_PATH.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def add_to_startup():
    try:
        # Create shortcut in startup folder
        startup_folder = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
        shortcut_path = os.path.join(startup_folder, "WallpaperChanger.lnk")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = sys.executable
        shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
        shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        shortcut.save()
        
        logging.info("Added to startup successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to add to startup: {e}")
        return False

def create_save_directory():
    try:
        SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        logging.info(f"Using directory: {SAVE_DIRECTORY}")
        return True
    except Exception as e:
        logging.error(f"Error creating directory {SAVE_DIRECTORY}: {e}")
        return False

def cleanup_old_wallpapers():
    try:
        # Keep only the 10 most recent wallpapers
        wallpapers = list(SAVE_DIRECTORY.glob('*'))
        wallpapers.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for wallpaper in wallpapers[10:]:
            try:
                wallpaper.unlink()
                logging.info(f"Deleted old wallpaper: {wallpaper}")
            except Exception as e:
                logging.warning(f"Failed to delete {wallpaper}: {e}")
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

def fetch_wallpaper(tag, resolution, retry_count=0):
    params = {
        "count": 1,
        "tag": tag,
        "resolution": resolution
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and data:
            return data[0].get('download_url')
        elif isinstance(data, dict):
            wallpapers = data.get('wallpapers', [])
            if wallpapers:
                return random.choice(wallpapers).get('download_url')
                
        logging.warning(f"No wallpapers found for tag '{tag}' and resolution '{resolution}'")
        return None
    
    except Exception as e:
        logging.error(f"Error fetching wallpaper: {e}")
        if retry_count < MAX_RETRIES:
            logging.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            return fetch_wallpaper(tag, resolution, retry_count + 1)
        return None

def set_wallpaper(image_path):
    try:
        SPI_SETDESKWALLPAPER = 20
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 
            0, 
            str(image_path), 
            3
        )
        logging.info(f"Wallpaper set to: {image_path}")
        return True
    except Exception as e:
        logging.error(f"Error setting wallpaper: {e}")
        return False

def download_wallpaper(url, retry_count=0):
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
        if retry_count < MAX_RETRIES:
            logging.info(f"Retrying download in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            return download_wallpaper(url, retry_count + 1)
        return None

def main():
    setup_logging()
    logging.info("Starting Wallpaper Changer")
    
    if not create_save_directory():
        return
    
    # Add to startup programs
    add_to_startup()
    
    while True:
        try:
            # Cleanup old wallpapers
            cleanup_old_wallpapers()
            
            # Select random tag and resolution
            tag = random.choice(TAGS)
            resolution = random.choice(RESOLUTIONS)
            logging.info(f"Fetching wallpaper with tag '{tag}' and resolution '{resolution}'")
            
            # Fetch and set wallpaper
            wallpaper_url = fetch_wallpaper(tag, resolution)
            if wallpaper_url:
                save_path = download_wallpaper(wallpaper_url)
                if save_path:
                    set_wallpaper(save_path)
            
            # Wait for the specified interval
            logging.info(f"Waiting {CHANGE_INTERVAL} seconds before next change")
            time.sleep(CHANGE_INTERVAL)
            
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
            logging.info(f"Restarting in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
