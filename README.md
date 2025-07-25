# Nexus AutoDL

<p align="center">
  <img alt="Nexus AutoDL Logo" src="https://raw.githubusercontent.com/parsiad/nexus-autodl/master/assets/img/logo.png">
</p>

<p align="center">
  <!-- These badges are customized for your repository -->
  <a href="https://github.com/1Tdd/nexus-autodl/releases"><img alt="Latest Release" src="https://img.shields.io/github/v/release/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/blob/main/LICENSE"><img alt="GitHub License" src="https://img.shields.io/github/license/1Tdd/nexus-autodl?style=for-the-badge"></a>
</p>

Nexus AutoDL is an autoclicker designed to automate the process of downloading mods from [Nexus Mods](https://nexusmods.com). When using tools like [Wabbajack](https://www.wabbajack.org) or [Portmod](https://gitlab.com/portmod/portmod), modlists can contain hundreds of files, requiring a manual click for each one. This tool automates that tedious process for you.

While Nexus AutoDL is running, any time a mod or collection download page is visible on your screen, it will find and click the download button, letting you step away while your modlist downloads.

If you find this tool useful, please **leave a star on GitHub** to help others discover it!

---

## ✨ Key Features

*   **Full Control with Pause & Resume:**
    *   **`F3` Key:** Start or Resume the process.
    *   **`F4` Key:** Pause the process at any time.
*   **Modern Dark Mode Interface:** A sleek, comfortable dark theme for the entire application.
*   **Non-Intrusive Operation:** The mouse cursor automatically returns to its original position after each click, so the bot doesn't get in your way.
*   **Configuration is Saved:** The app remembers your last-used templates folder, so you don't have to select it every time.
*   **Smart and Stable:** With input validation and a robust single-threaded architecture, the application is designed to be stable and crash-free.
*   **Human-like Clicks:** Clicks are slightly randomized to appear more natural.

<p align="center">
  <img alt="App Screenshot" src="https://github.com/user-attachments/assets/959c758e-7874-47a7-991e-6d14ebfddd21" width="600">
  <br><em>The new dark mode interface in action.</em>
</p>

## 🚀 Getting Started

### For Windows Users (Recommended)

1.  **Download the `.exe`:** Go to the [**Releases Page**](https://github.com/1Tdd/nexus-autodl/releases) and download the `nexus_autodl.exe` file from the latest release.
2.  **Prepare Your Templates:**
    *   Create a folder anywhere you like (e.g., on your Desktop).
    *   Take a screenshot of the download button you want to click (a great tool is the Windows Snipping Tool, **`Win`+`Shift`+`S`**).
    *   Save this image (e.g., `download_button.png`) inside the folder you just created. You can add multiple images for different buttons.
3.  **Run the App:**
    *   Double-click `nexus_autodl.exe` to start the application.
    *   Use the **`...`** button to select the folder containing your template images. The app will remember this choice for next time.
    *   Press **`F3`** to start!

## 🎮 How to Use

1.  **Configure Settings:** Adjust options like `Confidence` or `Sleep` times in the main window if needed.
2.  **Start/Resume:** Press the **`F3`** key. A log console will appear, and the script will begin searching for your template images.
3.  **Pause:** Press the **`F4`** key. The script will pause its activity until you resume.
4.  **Close the Application:** Simply close the main window or the log console using the "X" button.

## ⚡ Maximizing Automation (Optional)

For a truly seamless, zero-wait download experience, you can use this autoclicker in combination with a user script that bypasses the 5-second countdown on Nexus Mods.

*   **Recommended Tool:** [**Nexus No Wait**](https://greasyfork.org/it/scripts/519037-nexus-no-wait) on Greasy Fork.

By using both tools together, Nexus AutoDL will click the download button, and the "Nexus No Wait" script will ensure the download starts instantly, creating a fully automated workflow.

## ❤️ A Note on Supporting Nexus Mods

Nexus Mods is an incredible platform run by a dedicated team. **The absolute best way to give back to the community and support the site is by purchasing a [Premium Membership](https://www.nexusmods.com/users/premium).** This gives you uncapped download speeds, removes ads, and directly funds the platform's development and maintenance.

This tool is offered as a convenience for those who may not be in a position to subscribe but still face the challenge of downloading large modlists. If you can, please consider supporting Nexus Mods for their amazing service.

## ⚠️ Caution: Use at Your Own Risk

Using a bot to download from Nexus Mods is in direct violation of their Terms of Service:

> "Attempting to download files or otherwise record data offered through our services (including but not limited to the Nexus Mods website and the Nexus Mods API) in a fashion that drastically exceeds the expected average, through the use of software automation or otherwise, is prohibited without expressed permission. Users found in violation of this policy will have their account suspended."

This tool is provided for educational and convenience purposes. The user assumes all risk and responsibility for its use. The authors and contributors are not responsible for any account suspension or other consequences.

## 🛠️ Building the .exe from source

If you want to compile your own executable from the source code, you will need `pyinstaller`.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```2.  **Run the build command from the project directory:**
    ```bash
    pyinstaller --onefile --windowed --name nexus_autodl nexus_autodl.py
    ```
3.  Your finished `.exe` will be located in the `dist` folder.
