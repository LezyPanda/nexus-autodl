# Nexus AutoDL

<p align="center">
  <img alt="Nexus AutoDL Logo" src="https://raw.githubusercontent.com/parsiad/nexus-autodl/master/assets/img/logo.png">
</p>

<p align="center">
  <a href="https://github.com/1Tdd/nexus-autodl/releases"><img alt="Latest Release" src="https://img.shields.io/github/v/release/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/blob/main/LICENSE"><img alt="GitHub License" src="https://img.shields.io/github/license/1Tdd/nexus-autodl?style=for-the-badge"></a>
</p>

> **Note:** This project is a enhanced fork of the original [Nexus AutoDL by parsiad](https://github.com/parsiad/nexus-autodl). A huge thank you to the original creator for laying the foundation for this useful tool.

Nexus AutoDL is an autoclicker designed to automate the process of downloading mods from [Nexus Mods](https://nexusmods.com). When using tools like [Wabbajack](https://www.wabbajack.org), modlists can contain hundreds of files, requiring a manual click for each one. This tool automates that tedious process for you.

If you find this tool useful, please **leave a star on GitHub** to help others discover it!

---

## ✨ Key Features

*   **Integrated Template Creation:** No more manual screenshots! Click "Create Template", drag a box around any element on your screen, and save it instantly.
*   **Full Control with Pause & Resume:**
    *   **`F3` Key:** Start or Resume the process.
    *   **`F4` Key:** Pause the process at any time.
*   **Customizable Visual Feedback:** Get instant confirmation with a colored border that flashes around matched templates. You can customize the color and duration!
*   **Modern Dark Mode Interface:** A sleek, comfortable dark theme for the entire application, professionally organized for clarity.
*   **Dynamic Config Window:** When you pause, the main window reappears, allowing you to change settings like "Always on Top" mid-session.
*   **Full Settings Persistence:** The app remembers all your settings (confidence, sleep times, paths, and toggles) between sessions.
*   **Non-Intrusive Operation:** The mouse cursor automatically returns to its original position after each click.

<p align="center">
  <img alt="App Screenshot" src="https://github.com/user-attachments/assets/2d866425-47b9-4c82-b136-a20b1f0d9e83" width="600">
  <br><em>The v0.5.1 interface in action.</em>
</p>

## 🚀 Getting Started

### For Windows Users (Recommended)

1.  **Download the `.exe`:** Go to the [**Releases Page**](https://github.com/1Tdd/nexus-autodl/releases) and download the `nexus_autodl.exe` file from the latest release.
2.  **Run the App:**
    *   Double-click `nexus_autodl.exe` to start.
    *   Use the **`Create Template`** button to easily capture the download buttons you want to click.
    *   Alternatively, you can manually place screenshot images in a folder and select it with the **`...`** button.
3.  **Start Automating:**
    *   Press **`F3`** to start!

## 🎮 How to Use

1.  **Configure Settings:** Adjust options like `Confidence`, `Sleep` times, or `Always on Top` in the main window if needed.
2.  **Start/Resume:** Press the **`F3`** key. A log console will appear, and the script will begin searching for your template images.
3.  **Pause:** Press the **`F4`** key. The main window will reappear, allowing you to change settings.
4.  **Close the Application:** Simply close the main window or the log console using the "X" button. This will automatically save your settings.

## ⚡ Maximizing Automation (Optional)

For a truly seamless, zero-wait download experience, you can use this autoclicker in combination with a user script that bypasses the 5-second countdown on Nexus Mods.

*   **Recommended Tool:** [**Nexus No Wait**](https://greasyfork.org/it/scripts/519037-nexus-no-wait) on Greasy Fork.

By using both tools together, Nexus AutoDL will click the download button, and the "Nexus No Wait" script will ensure the download starts instantly, creating a fully automated workflow.

## ❤️ A Note on Supporting Nexus Mods

Nexus Mods is an incredible platform run by a dedicated team. **The absolute best way to give back to the community and support the site is by purchasing a [Premium Membership](https://www.nexusmods.com/users/premium).** This gives you uncapped download speeds, removes ads, and directly funds the platform's development and maintenance.

This tool is offered as a convenience for those who may not be in a position to subscribe but still face the challenge of downloading large modlists. If you can, please consider supporting Nexus Mods for their amazing service.

## ⚠️ Caution: Use at Your Own Risk

Using a bot to download from Nexus Mods is in direct violation of their Terms of Service. This tool is provided for educational and convenience purposes. The user assumes all risk and responsibility for its use. The authors and contributors are not responsible for any account suspension or other consequences.

## 🛠️ Building the .exe from source

If you want to compile your own executable from the source code, you will need `pyinstaller`.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
2.  **Run the build command from the project directory:**
    ```bash
    pyinstaller --onefile --windowed --name nexus_autodl nexus_autodl.py
    ```
3.  Your finished `.exe` will be located in the `dist` folder.
