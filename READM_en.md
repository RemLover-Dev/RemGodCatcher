# Rem God Catcher ❄️

Rem God Catcher is a powerful, cross-platform image downloading tool designed to interact with various imageboard APIs. It features a modern, glass-morphism Web UI (powered by Eel) and a robust Python backend capable of batch-downloading images with advanced tag filtering.

## 🌟 Features

* **Multi-Platform Support:** Built-in modules for Rule34, Safebooru, Zerochan, Waifu.im, and Nekos.best.
* **Modern GUI:** A sleek, dark-themed web interface with a built-in terminal log and tabbed navigation.
* **Advanced Search Logic:** * Support for `AND` & `OR` (`~`) tag queries.
  * Tag exclusions (e.g., `-video`, `-gif`).
  * Custom sorting (Score, ID, Ascending, Descending).
* **Titan Engine:** Features anti-ban protections, tactical delays, and a resilient retry-loop to handle slow networks and API rate limits.

---

## 🎨 How to Customize Background Images (Wallpapers)

The Web UI changes its background wallpaper dynamically depending on the tab you are currently browsing. To personalize these wallpapers with your own images:

1. Navigate to the `web/wallpaper/` directory.
2. Replace the default placeholder files with your own images. **You must keep the exact same filenames and extensions** listed below:

```text
web/wallpaper/
├── Rem_main.png     <- Main / System Setup Tab
├── Rem_neko.jpg     <- Nekos.best Tab
├── Rem_zero.jpg     <- Zerochan Tab
├── Rem_waifu.png    <- Waifu.im Tab
├── Rem_safe.jpg     <- Safebooru Tab
└── Rem_rule34.jpg   <- Rule34 Tab
```
Restart the application to see your custom themes in action!

## 🔑 How to get your Rule34 API Key & User ID

To use the Rule34 downloader at maximum efficiency and bypass anonymous limits, you need to input your `api_key` and `user_id` inside the `Rem_catcher.py` or `Rule.py` file. Here is how to find them:

1. **Create an Account:** Go to [Rule34.xxx](https://rule34.xxx) and register for a free account.
2. **Find Your User ID:** * Log into your account and go to your **Profile** (My Account).
   * Look at the URL in your browser. It will look something like this: `https://rule34.xxx/index.php?page=account&s=profile&id=123456`.
   * The number at the very end (`123456`) is your **User ID**.
3. **Generate Your API Key:**
   * Go to **Settings** (or My Account options).
   * Scroll down until you find the **API Key** section.
   * Click **Generate API Key**. 
   * Copy the long string of text. This is your **API Key**.
4. **Insert into the Code:**
   * Open `Rem_catcher.py` (or `Rule.py`).
   * Find the variables `RULE34_USER_ID` and `RULE34_API_KEY` (or `client.user_id` and `client.api_key`).
   * Paste your credentials between the quotation marks. **Never share these keys publicly!**

---

## 📦 Installation & Usage

1. Clone this repository:
   ```bash
   git clone [https://github.com/YourUsername/Rem-God-Catcher.git](https://github.com/YourUsername/Rem-God-Catcher.git)
   cd Rem-God-Catcher
   ```

2. Install the required Python dependencies:
```bash
pip install eel requests urllib3 customtkinter rule34Py
```

3. Launch the graphical interface:
```bash
python Rem_catcher.py
```

## ⚠️ Disclaimer & Terms of Use

* **Educational Purposes:** This software is provided for educational and archiving purposes only.
* **NSFW Content:** Some of the APIs supported by this tool index Not Safe For Work (NSFW) content. Users must be of legal age in their jurisdiction to use the tool for such purposes.
* **API Limits:** This tool is designed to respect the target servers by using rate-limiting and tactical pauses. Please do not modify the code to aggressively spam requests.

## 📄 License

MIT License

```
این ترکیب دقیقاً به کاربران گیت‌هاب می‌فهماند که چطور ظاهر برنامه را شخصی‌سازی کنند و از طرفی کلیدهای API خود را چطور بسازند، در حالی که عکس شخصی تو در سیستم گیت‌هاب بلاک شده و آپلود نمی‌شود. عالی است!
```
