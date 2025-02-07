import os
import sys
import random
import requests
import ctypes
import platform
import subprocess
import logging
import json
from datetime import datetime

class WallpaperManager:
    def __init__(self):
        """Initialize the wallpaper manager and set up required directory structure."""
        # Define base directory and subdirectories
        self.base_dir = os.path.join(os.path.expanduser('~'), 'WallwidgyWallpapers')
        self.images_dir = os.path.join(self.base_dir, 'images')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.history_file = os.path.join(self.base_dir, 'wallpaper_history.json')
        
        # Create directory structure
        self._create_directory_structure()
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize wallpaper history
        self.used_wallpapers = self._load_history()
        
        logging.info("WallpaperManager initialized successfully")

    def _create_directory_structure(self):
        """Create necessary directories if they don't exist."""
        try:
            # Create all required directories
            os.makedirs(self.images_dir, exist_ok=True)
            os.makedirs(self.logs_dir, exist_ok=True)
            
            # Create history file if it doesn't exist
            if not os.path.exists(self.history_file):
                with open(self.history_file, 'w') as f:
                    json.dump([], f)
        except Exception as e:
            print(f"Error creating directory structure: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Configure logging system."""
        log_file = os.path.join(self.logs_dir, 'wallpaper_changer.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s'
        )

    def _load_history(self):
        """Load the wallpaper history from JSON file."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading wallpaper history: {e}")
            return []

    def _save_history(self):
        """Save the wallpaper history to JSON file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.used_wallpapers, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving wallpaper history: {e}")

    def is_wallpaper_used(self, wallpaper_url):
        """Check if wallpaper has been used before."""
        return wallpaper_url in self.used_wallpapers

    def add_wallpaper(self, wallpaper_url):
        """Add a wallpaper to the history."""
        if wallpaper_url not in self.used_wallpapers:
            self.used_wallpapers.append(wallpaper_url)
            self._save_history()

    def get_random_wallpaper(self):
        """Fetch a random wallpaper that hasn't been used before."""
        resolutions = ['1080p', '1440p', '4k', '8k']
        max_attempts = 10
        
        for attempt in range(max_attempts):
            resolution = random.choice(resolutions)
            base_url = "https://www.wallwidgy.me/api/random-wallpapers"
            
            params = {
                "count": 1,
                "tag": "desktop",
                "resolution": resolution
            }
            
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                
                wallpapers = response.json()
                
                if not wallpapers:
                    logging.error("No wallpapers found.")
                    continue
                
                wallpaper = wallpapers[0]
                download_url = wallpaper.get('download_url')
                
                if not download_url:
                    logging.error("No download URL found for the wallpaper.")
                    continue
                
                if self.is_wallpaper_used(download_url):
                    logging.info(f"Skipping previously used wallpaper: {download_url}")
                    continue
                
                logging.info(f"Selected Resolution: {resolution}")
                return download_url
            
            except requests.RequestException as e:
                logging.error(f"Error fetching wallpaper: {e}")
                continue
        
        logging.error("Failed to find unused wallpaper after maximum attempts")
        return None

    def download_wallpaper(self, url):
        """Download the wallpaper from the given URL."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = os.path.splitext(url)[1] or '.jpg'
            filename = f'wallpaper_{timestamp}{file_extension}'
            full_path = os.path.join(self.images_dir, filename)
            
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

    def set_wallpaper(self, file_path):
        """Set the wallpaper based on the operating system."""
        if not file_path or not os.path.exists(file_path):
            logging.error("Invalid file path.")
            return False
        
        system = platform.system().lower()
        
        try:
            if system == 'windows':
                ctypes.windll.user32.SystemParametersInfoW(20, 0, file_path, 3)
            elif system == 'darwin':  # macOS
                script = f'tell application "System Events" to set picture of every desktop to "{file_path}"'
                subprocess.run(['osascript', '-e', script])
            elif system == 'linux':
                desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
                
                if 'gnome' in desktop_env:
                    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{file_path}'])
                elif 'kde' in desktop_env:
                    script = f'var a = activities.currentActivity(); for (var i in desktops()) {{ desktops()[i].wallpaperPlugin = "org.kde.image"; desktops()[i].currentWallpaper = "{file_path}"; }}'
                    subprocess.run(['qdbus', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script])
                else:
                    logging.error(f"Unsupported Linux desktop environment: {desktop_env}")
                    return False
            
            logging.info(f"Wallpaper successfully set from: {file_path}")
            return True
        
        except Exception as e:
            logging.error(f"Error setting wallpaper: {e}")
            return False

def main():
    """Main function to fetch and set a random wallpaper."""
    try:
        # Initialize wallpaper manager (this will create all necessary directories)
        manager = WallpaperManager()
        logging.info("Wallpaper changer started")
        
        # Fetch unique wallpaper URL
        wallpaper_url = manager.get_random_wallpaper()
        if not wallpaper_url:
            logging.error("Failed to fetch wallpaper.")
            sys.exit(1)
        
        # Download wallpaper
        wallpaper_path = manager.download_wallpaper(wallpaper_url)
        if not wallpaper_path:
            logging.error("Failed to download wallpaper.")
            sys.exit(1)
        
        # Set wallpaper
        if manager.set_wallpaper(wallpaper_path):
            manager.add_wallpaper(wallpaper_url)
            logging.info("Wallpaper change completed successfully")
        else:
            logging.error("Failed to set wallpaper.")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()