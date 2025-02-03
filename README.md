# Auto Wallpaper Changer Service

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/)
[![WallWidgy API](https://img.shields.io/badge/WallWidgy-API-orange)](https://www.wallwidgy.me/)

A Windows service that automatically updates your desktop wallpaper at set intervals using the WallWidgy API. Keep your desktop fresh with minimal effort!

## Features

- Automatic wallpaper updates at configurable intervals
- Customizable image tags and resolutions via WallWidgy API
- Runs silently in the background as a Windows Service
- Simple configuration and setup
- Built-in error logging for easy troubleshooting

## Prerequisites

- Python 3.6 or higher
- Windows Operating System
- Administrator privileges for service installation

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/asifahamed11/auto-wallpaper-changer.git
   cd auto-wallpaper-changer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure settings**
   Open `change_wallpaper.py` and adjust the configuration:
   ```python
   API_ENDPOINT = "https://www.wallwidgy.me/api/random-wallpapers"
   TAGS = ["desktop"]  # Options: "desktop", "mobile", "recent"
   RESOLUTIONS = ["1080p", "1440p", "4k"]  # Options: "1080p", "1440p", "4k", "8k"
   SAVE_DIRECTORY = r"C:\Users\Admin\Pictures\Wallpapers"
   ```

## Service Management

### Installation

Open an administrative Command Prompt and run:
```bash
python change_wallpaper.py install
```

### Basic Commands

```bash
# Start the service
python change_wallpaper.py start

# Stop the service
python change_wallpaper.py stop

# Remove the service
python change_wallpaper.py remove
```

## Auto-Start Configuration

### Using Services Manager (Recommended)
1. Press `Win + R`, type `services.msc`, and press Enter
2. Find "Wallpaper Changer Service"
3. Right-click → Properties
4. Set "Startup type" to "Automatic"
5. Click Apply → OK

### Using Command Prompt
```bash
# Run as Administrator
sc config "WallpaperChangerService" start=auto
```

## Troubleshooting

1. **Service Not Starting?**
   - Verify Python installation
   - Check Windows Event Viewer for errors
   - Ensure you have admin privileges

2. **No Wallpaper Changes?**
   - Confirm internet connectivity
   - Verify API endpoint accessibility
   - Check save directory permissions

## Dependencies

```plaintext
requests==2.31.0
pywin32==306
```

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Developer**: Asif Ahamed
- **Email**: asifahamedstudent@gmail.com
- **GitHub**: [@asifahamed11](https://github.com/asifahamed11)

---

💡 **Pro Tip**: Set the service to "Automatic (Delayed Start)" if you experience any startup conflicts with other services.
