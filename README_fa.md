<div dir="rtl" align="center">

# Rem God Catcher

**ابزار مدرن دانلود تصویر با رابط کاربری شیشه‌ای وب**

پشتیبانی از Rule34، Safebooru، Zerochan، Waifu.im و Nekos.best با لاگ بلادرنگ، فیلتر پیشرفته تگ و محافظت ضدبن.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)

[English](README.md) | [فارسی](README_fa.md)

</div>

---

<div dir="rtl">

## امکانات

- **چندپلتفرمه** -- ماژول‌های داخلی برای ۵ بوئورد تصویر
- **وب رابط مدرن** -- تم تاریک شیشه‌ای، در مرورگر پیش‌فرض باز میشه
- **لاگ بلادرنگ** -- خروجی کنسول زنده از طریق WebSocket (Socket.IO)
- **جستجوی پیشرفته** -- کوئری تگ AND/OR، حذف تگ (`-video`, `-gif`)، سورت سفارشی
- **موتور ضدبن** -- وقفه‌های تاکتیکی، حلقه تلاش مجدد، مدیریت محدودیت API
- **پشتیبانی پروکسی** -- تنظیمات کامل پروکسی از رابط کاربری (v2rayN, Clash و غیره)
- **مدیریت کلید API** -- مدیریت اعتبارنامه Rule34 مستقیماً از رابط وب
- **پیشنهاد خودکار تگ** -- autocomplete زنده برای همه پلتفرم‌ها
- **ذخیره تنظیمات** -- پروکسی، کلیدها و تنظیمات دانلود در فایل `.env` ذخیره میشن

---

## شروع سریع

### ۱. کلون مخزن

```bash
git clone https://github.com/YourUsername/Rem-God-Catcher.git
cd Rem-God-Catcher
```

### ۲. نصب وابستگی‌ها

```bash
pip install flask flask-socketio requests urllib3 python-dotenv rule34Py
```

### ۳. تنظیمات (اختیاری)

فایل `.env` رو ویرایش کن یا از تب **API Keys** در رابط وب استفاده کن:

```env
RULE34_API_KEY=کلید_api_خود_را_اینجا_بگذارید
RULE34_USER_ID=شناسه_کاربری_خود_را_اینجا_بگذارید
USE_PROXY=false
PROXY_URL=http://127.0.0.1:10808
VERIFY_TLS=false
```

### ۴. اجرا

```bash
python Rem_catcher.py
```

رابط وب خودکار در `http://127.0.0.1:5000` باز میشه.

---

## ساختار پروژه

```
Rem God Catcher/
├── Rem_catcher.py          # هسته پایتون (Flask + Socket.IO)
├── tags.json               # دیتابیس تگ‌های Waifu.im (نام → اسلاگ)
├── safe_tag_names.json     # دیتابیس آفلاین تگ‌های Safebooru
├── .env                    # کلیدهای API و تنظیمات پروکسی (git-ignored)
├── .gitignore
├── LICENSE
├── README.md               # مستندات انگلیسی
├── README_fa.md            # مستندات فارسی
├── CHANGELOG.md
└── web/
    ├── index.html           # HTML اصلی (تب‌ها، فرم‌ها، تنظیمات)
    ├── script.js            # منطق فرانت‌اند (Socket.IO + fetch API)
    ├── style.css            # تم تاریک شیشه‌ای (فونت Inter)
    ├── Fonts/               # فونت‌های آفلاین
    └── wallpaper/           # تصاویر پس‌زمینه هر تب
```

---

## پلتفرم‌های پشتیبانی شده

| پلتفرم | تگ‌ها | NSFW | توضیحات |
|---------|-------|------|---------|
| **Rule34** | جستجوی کامل با AND/OR، حذف، سورت | بله | نیاز به کلید API برای بهترین نتیجه |
| **Safebooru** | جستجوی استاندارد تگ | خیر | ممکنه به پروکسی نیاز داشته باشه (Cloudflare) |
| **Zerochan** | جستجوی تگ با پیشنهادات زنده | خیر | تلاش مجدد و محدودیت نرخ داخلی |
| **Waifu.im** | تبدیل نام به اسلاگ، فیلتر NSFW | بله | از `tags.json` محلی برای پیشنهادات استفاده میکنه |
| **Nekos.best** | دسته‌بندی (PNG / GIF) | خیر | پشتیبانی چند فرمت |

---

## سفارشی‌سازی

### تصاویر پس‌زمینه

تصاویر داخل پوشه `web/wallpaper/` رو جایگزین کن با حفظ دقیق نام فایل‌ها:

| فایل | تب |
|------|-----|
| `Rem_main.png` | صفحه اصلی / تنظیمات سیستم |
| `Rem_neko.jpg` | Nekos.best |
| `Rem_zero.jpg` | Zerochan |
| `Rem_waifu.png` | Waifu.im |
| `Rem_safe.jpg` | Safebooru |
| `Rem_rule34.jpg` | Rule34 |

---

## دریافت کلید API Rule34

1. در [rule34.xxx](https://rule34.xxx) ثبت‌نام کن
2. به **My Account** -> **Settings** برو
3. بخش **API Key** رو پیدا کن -> **Generate API Key** رو بزن
4. **شناسه کاربری (User ID)** رو از آدرس پروفایل کپی کن
5. هر دو رو در تب **API Keys** رابط وب وارد کن

> هرگز کلیدهای API خود رو عمومی نکن.

---

## وابستگی‌ها

| بسته | نسخه | کاربرد |
|------|------|--------|
| `flask` | 3.x | سرور وب |
| `flask-socketio` | 5.x | ارتباط بلادرنگ WebSocket |
| `requests` | 2.x | کلاینت HTTP |
| `urllib3` | 2.x | استراتژی‌های تلاش مجدد |
| `python-dotenv` | 1.x | بارگذاری فایل `.env` |
| `rule34Py` | latest | کتابخانه API Rule34 |

---

## سلب مسئولیت

این نرم‌افزار صرفاً برای **اهداف آموزشی و بایگانی** ارائه شده است. برخی از APIهای پشتیبانی شده شامل محتوای NSFW هستند -- کاربران باید در حوزه قضایی خود بزرگسال باشند. لطفاً از محدودیت نرخ APIها احترام بگذارید و درخواست‌های پرتکرار ارسال نکنید.

---

## مجوز

[MIT License](LICENSE)

</div>
