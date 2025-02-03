import win32serviceutil
import win32service
import win32event
import servicemanager
import requests
import random
import ctypes
import os
import time

# Configuration
API_ENDPOINT = "https://www.wallwidgy.me/api/random-wallpapers"
TAGS = ["desktop"]
RESOLUTIONS = ["1080p", "1440p", "4k"]
SAVE_DIRECTORY = r"C:\Users\Admin\Pictures\Wallpapers"

def create_save_directory():
    if not os.path.exists(SAVE_DIRECTORY):
        try:
            os.makedirs(SAVE_DIRECTORY)
        except Exception as e:
            servicemanager.LogError(f"Error creating directory {SAVE_DIRECTORY}: {e}")
            return False
    return True

def fetch_wallpaper(tag, resolution):
    # (Same as before)
    pass

def set_wallpaper(image_path):
    # (Same as before)
    pass

class WallpaperService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WallpaperChangerService"
    _svc_display_name_ = "Wallpaper Changer Service"
    _svc_description_ = "Changes desktop wallpaper automatically."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        if not create_save_directory():
            return
        while self.running:
            tag = random.choice(TAGS)
            resolution = random.choice(RESOLUTIONS)
            wallpaper_url = fetch_wallpaper(tag, resolution)
            if wallpaper_url:
                filename = os.path.basename(wallpaper_url)
                save_path = os.path.join(SAVE_DIRECTORY, filename)
                try:
                    response = requests.get(wallpaper_url, timeout=10)
                    response.raise_for_status()
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    set_wallpaper(save_path)
                except Exception as e:
                    servicemanager.LogError(f"Error downloading or setting wallpaper: {e}")
            time.sleep(100) ##time in seconds

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(WallpaperService)