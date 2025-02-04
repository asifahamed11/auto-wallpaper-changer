import os
import sys
import random
import requests
import ctypes
import platform
import subprocess
import logging
from datetime import datetime

# Configure logging
log_dir = os.path.join(os.path.expanduser('~'), 'WallwidgyWallpapers', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'wallpaper_changer.log')

logging.basicConfig(
    filename=log_file, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s'
)

def get_random_wallpaper():
    """
    Fetch a random wallpaper with a randomly selected resolution.
    """
    # Available resolutions
    resolutions = ['1080p', '1440p', '4k', '8k']
    
    # Randomly select a resolution
    resolution = random.choice(resolutions)
    
    base_url = "https://www.wallwidgy.me/api/random-wallpapers"
    
    # Parameters to get a unique desktop wallpaper
    params = {
        "count": 1,
        "tag": "desktop",
        "resolution": resolution
    }
    
    try:
        # Fetch wallpaper data
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        wallpapers = response.json()
        
        # Check if any wallpapers were returned
        if not wallpapers:
            logging.error("No wallpapers found.")
            return None
        
        # Get the wallpaper details
        wallpaper = wallpapers[0]
        download_url = wallpaper.get('download_url')
        
        if not download_url:
            logging.error("No download URL found for the wallpaper.")
            return None
        
        # Log the selected resolution
        logging.info(f"Selected Resolution: {resolution}")
        
        return download_url
    
    except requests.RequestException as e:
        logging.error(f"Error fetching wallpaper: {e}")
        return None

def download_wallpaper(url):
    """
    Download the wallpaper from the given URL.
    """
    try:
        # Ensure downloads directory exists
        download_dir = os.path.join(os.path.expanduser('~'), 'WallwidgyWallpapers')
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(url)[1] or '.jpg'
        filename = f'wallpaper_{timestamp}{file_extension}'
        full_path = os.path.join(download_dir, filename)
        
        # Download the wallpaper
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(full_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        logging.info(f"Wallpaper downloaded: {full_path}")
        return full_path
    
    except Exception as e:
        logging.error(f"Error downloading wallpaper: {e}")
        return None

def set_wallpaper(file_path):
    """
    Set the wallpaper based on the operating system.
    """
    if not file_path or not os.path.exists(file_path):
        logging.error("Invalid file path.")
        return False
    
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            # Update with persistence flags (3 = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
            ctypes.windll.user32.SystemParametersInfoW(20, 0, file_path, 3)
        elif system == 'darwin':  # macOS
            script = f'tell application "System Events" to set picture of every desktop to "{file_path}"'
            subprocess.run(['osascript', '-e', script])
        elif system == 'linux':
            # For most Linux desktop environments
            desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            if 'gnome' in desktop_env:
                subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{file_path}'])
            elif 'kde' in desktop_env:
                subprocess.run(['qdbus', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', 
                                f'var a = activities.currentActivity(); for (var i in desktops()) {{ desktops()[i].wallpaperPlugin = "org.kde.image"; desktops()[i].currentWallpaper = "{file_path}"; }}'])
            else:
                logging.error(f"Unsupported Linux desktop environment: {desktop_env}")
                return False
        
        logging.info(f"Wallpaper successfully set from: {file_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error setting wallpaper: {e}")
        return False

def main():
    """
    Main function to fetch and set a random wallpaper.
    """
    logging.info("Wallpaper changer started")
    
    # Fetch wallpaper URL with random resolution
    wallpaper_url = get_random_wallpaper()
    
    if not wallpaper_url:
        logging.error("Failed to fetch wallpaper.")
        sys.exit(1)
    
    # Download wallpaper
    wallpaper_path = download_wallpaper(wallpaper_url)
    
    if not wallpaper_path:
        logging.error("Failed to download wallpaper.")
        sys.exit(1)
    
    # Set wallpaper
    if not set_wallpaper(wallpaper_path):
        logging.error("Failed to set wallpaper.")
        sys.exit(1)
    
    logging.info("Wallpaper change completed successfully")

if __name__ == "__main__":
    main()
