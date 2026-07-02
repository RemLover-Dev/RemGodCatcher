<div dir="rtl" align="center">

# Rem God Catcher

**ابزار مدرن دانلود تصویر و ویدیو با رابط کاربری شیشه‌ای وب**

پشتیبانی از Rule34، Safebooru، Gelbooru، Zerochan، Waifu.im، Nekos.best و Nekos.life با لاگ بلادرنگ، موتور کشف تگ، فیلتر پیشرفته و محافظت ضدبن.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)
[![Version](https://img.shields.io/badge/Version-3.1.0-ff9ff3.svg)](CHANGELOG.md)

[English](README.md) | [فارسی](README_fa.md)

</div>

---

<div dir="rtl">

## امکانات

- **چندپلتفرمه** -- ماژول‌های داخلی برای ۷ بوئورد تصویر
- **وب رابط مدرن** -- تم تاریک شیشه‌ای، در مرورگر پیش‌فرض باز میشه
- **موتور کشف و بایگانی** -- استخراج زنده تگ‌ها و نام هنرمندان از مدیای دانلود شده، نمایش داده شده در تب بایگانی تصاویر
- **علاقه‌مندی‌ها و تاریخچه جستجو** -- تگ‌ها رو به لیست علاقه‌مندی اضافه کن برای جستجوی یک‌کلیکی و تاریخچه جستجو رو حفظ کن
- **پشتیبانی ویدیو و GIF** -- فیلتر اختصاصی برای دانلود فرمت‌های `.mp4`، `.webm` و GIF
- **فیلتر فقط GIF** -- Rule34 از حالت فقط GIF به همراه Images/Videos/All پشتیبانی میکنه
- **لاگ بلادرنگ** -- خروجی کنسول زنده از طریق WebSocket (Socket.IO)
- **جستجوی پیشرفته** -- کوئری تگ AND/OR، حذف تگ (`-video`, `-image`)، سورت سفارشی، مرور دسته‌بندی
- **موتور ضدبن** -- وقفه‌های تاکتیکی، حلقه تلاش مجدد، مدیریت محدودیت API
- **پشتیبانی پروکسی** -- تنظیمات کامل پروکسی از رابط کاربری (v2rayN, Clash و غیره)
- **مدیریت کلید API** -- مدیریت اعتبارنامه Rule34 مستقیماً از رابط وب
- **پیشنهاد خودکار تگ** -- autocomplete زنده برای همه پلتفرم‌ها
- **ذخیره تنظیمات** -- پروکسی، کلیدها و تنظیمات دانلود در فایل `.env` ذخیره میشن

---

## شروع سریع

### ۱. کلون مخزن

```bash
git clone https://github.com/callmedark44/RemGodCatcher.git
cd RemGodCatcher
```

### ۲. نصب وابستگی‌ها

```bash
pip install flask flask-socketio requests urllib3 python-dotenv rule34Py
```

### ۳. تنظیمات (اختیاری)

فایل `.env` رو ویرایش کن یا از تب **Options** در رابط وب استفاده کن:

```env
RULE34_API_KEY=کلید_api_خود_را_اینجا_بگذارید
RULE34_USER_ID=شناسه_کاربری_خود_را_اینجا_بگذارید
USE_PROXY=false
PROXY_URL=http://127.0.0.1:10808
VERIFY_TLS=false
API_TIMEOUT=10
RETRY_WAIT=5
ANTI_BAN_PAUSE=3.0
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
├── shared.py               # ابزارهای مشترک، مدیریت تگ و پل ارتباطی لاگ
├── workers/                # ماژول‌های دانلود اختصاصی هر API
├── tags.json               # دیتابیس تگ‌های Waifu.im (نام → اسلاگ)
├── safe_tag_names.json     # دیتابیس آفلاین تگ‌های Safebooru
├── tag_history.json        # دیتابیس تاریخچه جستجو (git-ignored)
├── fav_tags.json           # دیتابیس علاقه‌مندی‌ها (git-ignored)
├── image_history.json      # بایگانی تگ تصاویر (git-ignored)
├── .env                    # کلیدهای API و تنظیمات پروکسی (git-ignored)
├── .gitignore
├── LICENSE
├── README.md               # مستندات انگلیسی
├── README_fa.md            # مستندات فارسی
├── CHANGELOG.md
└── web/
    ├── index.html           # HTML اصلی (تب‌ها، فرم‌ها، بایگانی، تنظیمات)
    ├── script.js            # منطق فرانت‌اند (Socket.IO + fetch API)
    ├── style.css            # تم تاریک شیشه‌ای (فونت Inter)
    ├── Fonts/               # فونت‌های آفلاین
    └── wallpaper/           # تصاویر پس‌زمینه هر تب
```

---

## پلتفرم‌های پشتیبانی شده

| پلتفرم | تگ‌ها | NSFW | توضیحات |
|---------|-------|------|---------|
| **Rule34** | جستجوی کامل با AND/OR، حذف، سورت، پشتیبانی فرمت ویدیو | بله | نیاز به کلید API برای بهترین نتیجه |
| **Safebooru** | جستجوی استاندارد تگ، پشتیبانی فرمت ویدیو، استخراج هنرمند | خیر | ممکنه به پروکسی نیاز داشته باشه (Cloudflare) |
| **Gelbooru** | جستجوی کامل، فیلتر فرمت، پشتیبانی ویدیو | بله | نیاز به کلید API برای بهترین نتیجه |
| **Zerochan** | جستجوی تگ با پیشنهادات زنده | خیر | تلاش مجدد و محدودیت نرخ داخلی |
| **Waifu.im** | تبدیل نام به اسلاگ، فیلتر NSFW | بله | از `tags.json` محلی برای پیشنهادات استفاده میکنه |
| **Nekos.best** | دسته‌بندی (PNG / GIF) | خیر | پشتیبانی چند فرمت |
| **Nekos.life** | دسته‌بندی با نشانگر نوع (GIF/Static/Mixed) | بله | نکو متحرک، هق‌هق، بغل، ناز و غیره |

---

## دریافت کلید API Rule34

1. در [rule34.xxx](https://rule34.xxx) ثبت‌نام کن
2. به **My Account** -> **Settings** برو
3. بخش **API Key** رو پیدا کن -> **Generate API Key** رو بزن
4. **شناسه کاربری (User ID)** رو از آدرس پروفایل کپی کن
5. هر دو رو در تب **Options** رابط وب وارد کن

> هرگز کلیدهای API خود رو عمومی نکن.

---

## سلب مسئولیت

این نرم‌افزار صرفاً برای **اهداف آموزشی و بایگانی** ارائه شده است. برخی از APIهای پشتیبانی شده شامل محتوای NSFW هستند -- کاربران باید در حوزه قضایی خود بزرگسال باشند. لطفاً از محدودیت نرخ APIها احترام بگذارید و درخواست‌های پرتکرار ارسال نکنید.

---

## مجوز

[MIT License](LICENSE)

</div>
