# 🌄 Windows Wallpaper Changer - WallWidgy API Integration  

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)  
[![Python Version](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/)  
[![WallWidgy API](https://img.shields.io/badge/WallWidgy-API-orange)](https://www.wallwidgy.me/)  

## 📌 Overview  
This **Windows-exclusive** wallpaper changer fetches high-quality wallpapers from **WallWidgy API** and updates your desktop background automatically. It ensures **no repetition**, downloads wallpapers to a dedicated folder, and logs all activity for easy tracking.  

## 🚀 Features  
✅ Fetches random wallpapers from **WallWidgy API**  
✅ Prevents repetition with a **history tracker**  
✅ Downloads and organizes wallpapers in a dedicated folder  
✅ **Automatically updates Windows wallpaper**  
✅ **Runs automatically using Task Scheduler**  
✅ Logs all actions for easy debugging  

---

## 🛠 Installation  

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/asifahamed11/wallpaper-changer.git
cd wallpaper-changer
```

### 2️⃣ Install Dependencies  
Ensure you have Python **3.6+** installed. Then, install the required Python library:  
```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Script  
```bash
python wallpaper_changer.py
```

---

## 🔄 Automate Using Windows Task Scheduler  

To make the wallpaper changer run **automatically**, follow these steps:  

### Step 1: Open Task Scheduler  
📷 ![Task Scheduler](tutorial_images/1.png)  

Press **Win + R**, type `taskschd.msc`, and press **Enter** to open the **Task Scheduler**.  

### Step 2: Create a Basic Task  
📷 ![Create Task](tutorial_images/2.png)  

Click **Create Basic Task...** in the right-hand **Actions** panel.  

### Step 3: Name and Describe the Task  
📷 ![Task Name](tutorial_images/3.png)  

- Name: **Wallpaper Changer**  
- Description: **Updates desktop background every hour**  
- Click **Next**  

### Step 4: Set the Trigger  
📷 ![Trigger](tutorial_images/4.png)  

- Choose **Daily**, click **Next**  
- Set **Start Time** (e.g., `7:50 PM`)  
- Ensure **Recur every: 1 days** is selected  
- Click **Next**  

### Step 5: Set the Action  
📷 ![Start Program](tutorial_images/5.png)  

- Choose **Start a program**, click **Next**  
- Browse to `run_wallpaper_changer.bat` file (e.g., `C:\Users\Admin\Pictures\WALL\run_wallpaper_changer.bat`)  
- Click **Next**  

### Step 6: Review the Task  
📷 ![Review Task](tutorial_images/6.png)  

Check **Open Properties when I click Finish**, then click **Finish**  

### Step 7: Edit Task Properties  
📷 ![Edit Properties](tutorial_images/7.png)  

- Find **Wallpaper Changer** task in **Task Scheduler Library**  
- Right-click and select **Properties**  

### Step 8: Configure Triggers  
📷 ![Trigger Edit](tutorial_images/8.png)  

- Go to **Triggers** tab → Click **Edit**  
- Set **Repeat task every: 1 hour**  
- Set **Duration: Indefinitely**  
- Click **OK**  

### Step 9: Configure Conditions  
📷 ![Power Conditions](tutorial_images/9.png)  

- Go to **Conditions** tab  
- Enable **Start only if the computer is on AC power**  
- Click **OK**  

### Step 10: Configure Security Options  
📷 ![Security](tutorial_images/10.png)  

- Go to **General** tab  
- Check **Run with highest privileges**  
- Click **OK**  

### Step 11: Verify Task in Task Scheduler Library  
📷 ![Verify Task](tutorial_images/11.png)  

Check if **Wallpaper Changer** appears in **Task Scheduler Library**  

### Step 12: Test the Task  
📷 ![Run Task](tutorial_images/12.png)  

Right-click the task → Select **Run** to test execution  

### Step 13: Check Task History  
📷 ![History](tutorial_images/13.png)  

Go to **History** tab to view execution logs  

### Step 14: Modify Task Settings if Needed  
📷 ![Modify Settings](tutorial_images/14.png)  

Right-click the task → Select **Properties** to change settings  

---

## ⚙️ How It Works  
1. The script initializes and creates necessary directories:  
   📂 **Wallpapers Folder:** `C:\Users\Admin\WallwidgyWallpapers\images\`  
   📂 **Logs Folder:** `C:\Users\Admin\WallwidgyWallpapers\logs\`  
2. Fetches a **random, unused wallpaper** from **WallWidgy API**.  
3. Downloads and saves it locally.  
4. Updates the **Windows wallpaper** using:  
   ```python
   ctypes.windll.user32.SystemParametersInfoW(20, 0, file_path, 3)
   ```
5. Logs all changes in:  
   ```txt
   C:\Users\Admin\WallwidgyWallpapers\logs\wallpaper_changer.log
   ```

---

## 🔧 Configuration  
Modify the **resolutions** in `get_random_wallpaper()` if you prefer specific quality:  
```python
resolutions = ['1080p', '1440p', '4k', '8k']
```

---

## 🐛 Troubleshooting  
🚨 **Wallpaper not changing?** Run the script as **Administrator**.  
🌐 **No internet?** Ensure you can access `https://www.wallwidgy.me/`.  
📜 **Logs?** Check `C:\Users\Admin\WallwidgyWallpapers\logs\wallpaper_changer.log`.  

---

## 📜 License  
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.  

---

## 💬 Connect  
👤 **Asif Ahamed**  
📧 [asifahamedstudent@gmail.com](mailto:asifahamedstudent@gmail.com)  
🐙 [GitHub](https://github.com/asifahamed11)  
