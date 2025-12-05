# Nexus AutoDL

<p align="center">
  <img alt="Nexus AutoDL Logo" src="https://raw.githubusercontent.com/parsiad/nexus-autodl/master/assets/img/logo.png">
</p>

<p align="center">
  <a href="https://github.com/1Tdd/nexus-autodl/releases"><img alt="Latest Release" src="https://img.shields.io/github/v/release/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/1Tdd/nexus-autodl?style=for-the-badge"></a>
  <a href="https://github.com/1Tdd/nexus-autodl/blob/main/LICENSE"><img alt="GitHub License" src="https://img.shields.io/github/license/1Tdd/nexus-autodl?style=for-the-badge"></a>
</p>

> **Note:** This project is a significantly enhanced fork of the original [Nexus AutoDL by parsiad](https://github.com/parsiad/nexus-autodl). A huge thank you to the original creator for laying the foundation for this powerful tool.

Nexus AutoDL is a versatile automation platform designed to automate repetitive clicking tasks. While it excels at downloading mods from [Nexus Mods](https://nexusmods.com) for tools like [Wabbajack](https://www.wabbajack.org), its powerful new features make it a perfect solution for any task that requires clicking on a series of images, from crafting in games to managing files.

If you find this tool useful, please **leave a star on GitHub** to help others discover it!

---

## ✨ Key Features

*   **Profile Management:** Create and switch between different **profiles**, each with its own unique set of templates and settings. Use one for Nexus, another for a game, and more!
*   **Powerful Search Modes:**
    *   **Priority Mode:** The bot intelligently searches for all templates in alphabetical order and clicks the first one it finds. Perfect for handling dynamic situations like pop-ups.
    *   **Sequence Mode:** For complex tasks, define an exact, step-by-step order for the bot to follow. It won't proceed to "Step 2" until "Step 1" is complete.
*   **Integrated Sequence Editor:** A dedicated UI panel that appears in Sequence Mode, allowing you to easily reorder your templates with "Move Up" and "Move Down" buttons.
*   **Per-Profile Settings:** Every profile saves its own unique settings! Your `Confidence`, `Sleep Times`, `Search Mode`, and `Sequence` order are all remembered.
*   **Instant Template Creation:** No more manual screenshots! Click "Create Template", drag a box around any element on your screen, and save it instantly to the active profile.
*   **Customizable Visual Feedback:** Get instant confirmation with a colored border that flashes around matched templates. You can customize the color and duration!
*   **Polished User Experience:** A sleek dark mode interface, full hotkey control (`F3`/`F4`), non-intrusive mouse behavior, and helpful tooltips for every setting.

<p align="center">
  <img alt="App Screenshot v0.6.3" src="https://github.com/user-attachments/assets/7d104ce2-fa0e-402f-ba26-6fcfc97a9696" width="600">
  <br><em>The v0.6.3 interface.</em>
</p>

## 🚀 Getting Started

1.  **Download the `.exe`:** Go to the [**Releases Page**](https://github.com/1Tdd/nexus-autodl/releases) and download the `nexus_autodl.exe` file from the latest release.
2.  **Run the App & Create a Profile:**
    *   Double-click `nexus_autodl.exe` to start.
    *   Open the **Profile Manager** via the "Manage..." button.
    *   Create your first profile (e.g., "Nexus Downloads").
3.  **Add Templates:**
    *   Use the **`Create Template`** button to easily capture the images you want the bot to click on.
4.  **Configure & Automate:**
    *   Choose your desired **Search Mode** and fine-tune any other settings.
    *   Press **`F3`** to start!

## 🎮 How to Use

1.  **Start/Resume:** Press **`F3`**. A log console will appear, and the script will begin.
2.  **Pause:** Press **`F4`**. The main window will reappear, allowing you to change settings.
3.  **Close:** Simply close the main window or the log console to exit. All your settings will be saved automatically.

## 💬 Community & Support

Your feedback is essential! If you encounter a problem or have an idea for a new feature, please get in touch.

*   **⭐ Star the Project:** If you like this app, give it a star on [the GitHub page](https://github.com/1Tdd/nexus-autodl)!
*   **🐞 Report a Bug:** Found an issue? [Open a new issue](https://github.com/1Tdd/nexus-autodl/issues/new/choose) and describe the problem in as much detail as possible.
*   **💡 Suggest a Feature:** Have a great idea for the next version? [Let me know](https://github.com/1Tdd/nexus-autodl/issues/new/choose)!
*   **📄 See the Changelog:** Want to know what's new? Check out the [Releases Page](https://github.com/1Tdd/nexus-autodl/releases).

## ⚡ Maximizing Automation (Optional)

For a truly seamless, zero-wait download experience on Nexus Mods, you can use this autoclicker in combination with a user script that bypasses the 5-second countdown.

*   **Recommended Tool:** [**Nexus No Wait**](https://greasyfork.org/it/scripts/519037-nexus-no-wait) on Greasy Fork.

## ❤️ A Note on Supporting Nexus Mods

Nexus Mods is an incredible platform. **The best way to support the site is by purchasing a [Premium Membership](https://www.nexusmods.com/users/premium).** This gives you uncapped download speeds, removes ads, and directly funds the platform. This tool is offered as a convenience for those who may not be in a position to subscribe but still face large modlists.

## ⚠️ Caution: Use at Your Own Risk

Using a bot to download from Nexus Mods is in direct violation of their Terms of Service. This tool is provided for educational and convenience purposes. The user assumes all risk and responsibility for its use.

## 🛠️ Running from Source

If you prefer to run the application directly from the source code:

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the Application:**
    You can run the application using the provided helper script:
    ```bash
    python run.py
    ```
    Or as a module:
    ```bash
    python -m nexus_autodl
    ```

## 🛠️ Building the .exe from source

If you want to compile your own executable from the source code, you will need `pyinstaller`.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
2.  **Run the build command from the project directory:**
    ```bash
    pyinstaller --onefile --windowed --name nexus_autodl run.py
    ```
3.  Your finished `.exe` will be located in the `dist` folder.

---

## Credits
[parsiad](https://github.com/parsiad) & [1Tdd](https://github.com/1Tdd)
