# 🌟 Wallpaper Service - Automated Desktop Wallpaper Changer  
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/)
[![WallWidgy API](https://img.shields.io/badge/WallWidgy-API-orange)](https://www.wallwidgy.me/)

## 🖼️ Overview  
**Wallpaper Service** is a lightweight Windows application that automatically updates your desktop wallpaper with high-quality images at regular intervals.  

## 🚀 Features  
- 🔄 **Auto Wallpaper Change:** Updates your desktop background every hour  
- 🎯 **High-Resolution Wallpapers:** Supports 1080p, 1440p, 4K, and 8K  
- 💾 **Wallpaper History:** Saves recent wallpapers in `~/WallwidgyWallpapers/`  
- 🖥️ **Multi-Platform Support:** Works on Windows, macOS, and Linux  

## 🔧 Detailed Installation

### Prerequisites
- Python 3.7+
- Windows 10/11
- Internet Connection

### 1. Install Python
1. Download from [python.org](https://www.python.org/downloads/)
2. **IMPORTANT**: Check "Add Python to PATH" during installation
3. Verify with `python --version` in Command Prompt

### 2. Install Required Library
```bash
pip install requests
```

### 3. Task Scheduler Configuration

#### Precise Setup Steps:
1. Open Task Scheduler
   - Press `Win + R`
   - Type `taskschd.msc`
   - Press Enter

2. In Task Scheduler Library
   - Click "Create Task" (not "Create Basic Task")
   - Name: "Wallpaper Changer"

3. Task Configuration
   - **General Tab:**
     * Run with highest privileges ✓
     * Configure for: Windows 10/11

   - **Triggers Tab:**
     * New Trigger
     * Daily
     * Repeat every: 1 hour
     * Duration: Indefinitely

   - **Conditions Tab:**
     * Start only if on AC power ✓
     * Stop if battery mode ✓

   - **Actions Tab:**
     * Action: Start a program
     * Program/Script: Path to `run_wallpaper_changer.bat`

4. Click "OK" and enter credentials if prompted

## 🛠️ Troubleshooting
- Python not found: Reinstall, ensure "Add to PATH"
- No wallpapers: Check internet connection
- Check logs: `~/WallwidgyWallpapers/logs/wallpaper_changer.log`

## 💡 Customization
Edit `wallpaper_changer.py` to:
- Change resolution preferences
- Modify download locations
- Add specific wallpaper tags

## 🖥️ Supported Platforms  
✅ Windows 10/11
✅ macOS
✅ Linux (Gnome, KDE)

## 📜 License  
MIT License

## 💬 Connect
👤 **Asif Ahamed**  
📧 [asifahamedstudent@gmail.com](mailto:asifahamedstudent@gmail.com)  
🐙 [GitHub](https://github.com/asifahamed11)
