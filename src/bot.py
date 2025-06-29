import json
import random
import string
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- خواندن متغیرهای محیطی با اعتبارسنجی ---
def get_env_int(key):
    val = os.getenv(key)
    if val is None:
        raise ValueError(f"متغیر محیطی {key} مقدار ندارد!")
    return int(val)

def get_env_str(key):
    val = os.getenv(key)
    if val is None:
        raise ValueError(f"متغیر محیطی {key} مقدار ندارد!")
    return val

API_ID = get_env_int("API_ID")
API_HASH = get_env_str("API_HASH")
BOT_TOKEN = get_env_str("BOT_TOKEN")
ADMIN_ID = get_env_int("ADMIN_ID")
CHANNEL_USERNAME = get_env_str("CHANNEL_USERNAME")
CARD_NUMBER = get_env_str("CARD_NUMBER")
CARD_OWNER = get_env_str("CARD_OWNER")

# --- اصلاح لینک کانال (حذف @ اگر هست) ---
channel_short = CHANNEL_USERNAME[1:] if CHANNEL_USERNAME.startswith("@") else CHANNEL_USERNAME

# --- شروع کلاینت Pyrogram ---
app = Client("mcstore_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- مقداردهی اولیه دیتای کاربرها ---
app.user_data = {}

# --- بارگذاری سفارشات ---
try:
    with open("orders.json", "r", encoding="utf-8") as f:
        orders = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    orders = []

# --- دسته‌بندی محصولات (شناسه انگلیسی و نام فارسی) ---
CATEGORIES = [
    ("premium", "پریمیوم"),
    ("stars", "استارز"),
    ("channel_member", "ممبر کانال"),
    ("group_member", "ممبر گروه"),
    ("boost", "بوست"),
    ("pv_message", "پیام پیوی"),
    ("reaction", "ری‌اکشن"),
    ("post_view", "ویو پست"),
    ("bot_stats", "آمار ربات"),
]

# --- منوی اصلی ---
def main_keyboard():
    buttons = [
        [InlineKeyboardButton(text=cat[1], callback_data=f"category_{cat[0]}") for cat in CATEGORIES[:3]],
        [InlineKeyboardButton(text=cat[1], callback_data=f"category_{cat[0]}") for cat in CATEGORIES[3:6]],
        [InlineKeyboardButton(text=cat[1], callback_data=f"category_{cat[0]}") for cat in CATEGORIES[6:]],
        [InlineKeyboardButton("شماره کارت پرداخت", callback_data="show_card")],
        [InlineKeyboardButton("درباره ربات", callback_data="about")],
    ]
    return InlineKeyboardMarkup(buttons)

# --- تولید کد رهگیری ---
def generate_tracking_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- چک جوین اجباری و شروع ---
@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    user = message.from_user
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ("left", "kicked"):
            await message.reply(
                f"برای استفاده از ربات باید ابتدا در کانال {CHANNEL_USERNAME} عضو شوید.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{channel_short}")]]
                )
            )
            return
    except Exception:
        await message.reply(
            f"برای استفاده از ربات باید ابتدا در کانال {CHANNEL_USERNAME} عضو شوید.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{channel_short}")]]
            )
        )
        return

    await message.reply(
        f"سلام {user.first_name} عزیز!\n"
        "به ربات خدمات مجازی MC-STORE خوش آمدید.\n"
        "از منوی زیر یکی از دسته‌ها را انتخاب کنید.",
        reply_markup=main_keyboard()
    )

# --- هندلر دکمه‌ها ---
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data.startswith("category_"):
        category_key = data.split("_", 1)[1]
        category_name = next((c[1] for c in CATEGORIES if c[0] == category_key), "نامشخص")
        await callback_query.message.edit(
            f"شما دسته‌ی «{category_name}» را انتخاب کردید.\n"
            "برای ثبت سفارش، لطفاً توضیحات سفارش خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")]]
            )
        )
        app.user_data[user_id] = {"category": category_key, "step": "waiting_order"}
        await callback_query.answer()

    elif data == "show_card":
        text = (
            f"شماره کارت برای پرداخت:\n"
            f"💳 {CARD_NUMBER}\n"
            f"نام صاحب کارت:\n"
            f"👤 {CARD_OWNER}\n\n"
            "پس از پرداخت، لطفاً رسید یا شماره پیگیری را ارسال کنید."
        )
        await callback_query.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")]]))
        await callback_query.answer()

    elif data == "about":
        text = (
            "ربات خدمات مجازی MC-STORE\n"
            "ارسال سفارش، دریافت رسید پرداخت و مدیریت توسط ادمین.\n"
            "ساخته شده توسط امیر"
        )
        await callback_query.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")]]))
        await callback_query.answer()

    elif data == "main_menu":
        await callback_query.message.edit(
            "از منوی زیر یکی از دسته‌ها را انتخاب کنید.",
            reply_markup=main_keyboard()
        )
        await callback_query.answer()

# --- هندلر دریافت پیام (ثبت سفارش و رسید) ---
@app.on_message(filters.private & ~filters.command("start"))
async def message_handler(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "ندارد"

    user_state = app.user_data.get(user_id)

    if user_state and user_state.get("step") == "waiting_order":
        order_text = message.text or ""
        if not order_text.strip():
            await message.reply("لطفاً توضیحات سفارش خود را به صورت متنی ارسال کنید.")
            return
        app.user_data[user_id]["order_text"] = order_text
        app.user_data[user_id]["step"] = "waiting_receipt"
        await message.reply(
            "توضیحات سفارش ثبت شد.\n"
            "لطفاً تصویر یا شماره پیگیری رسید پرداخت را ارسال کنید."
        )
        return

    if user_state and user_state.get("step") == "waiting_receipt":
        order_text = user_state.get("order_text", "")
        category_key = user_state.get("category", "unknown")
        category_name = next((c[1] for c in CATEGORIES if c[0] == category_key), category_key)
        tracking_code = generate_tracking_code()
        order = {
            "user_id": user_id,
            "user_name": user_name,
            "user_username": user_username,
            "category": category_name,
            "order_text": order_text,
            "receipt": None,
            "tracking_code": tracking_code
        }
        if message.photo:
            file_id = message.photo[-1].file_id if isinstance(message.photo, list) else message.photo.file_id
            order["receipt"] = {"type": "photo", "file_id": file_id}
        elif message.document:
            file_id = message.document.file_id
            order["receipt"] = {"type": "document", "file_id": file_id}
        elif message.text:
            order["receipt"] = {"type": "text", "content": message.text}
        else:
            await message.reply("لطفاً رسید را به صورت عکس، فایل یا متن ارسال کنید.")
            return

        orders.append(order)
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

        text = (
            f"سفارش جدید:\n"
            f"کاربر: {user_name} (@{user_username})\n"
            f"دسته: {order['category']}\n"
            f"توضیحات: {order_text}\n"
            f"کد رهگیری: {tracking_code}\n"
            f"رسید پرداخت:"
        )
        if order["receipt"]["type"] == "photo":
            await app.send_photo(ADMIN_ID, order["receipt"]["file_id"], caption=text)
        elif order["receipt"]["type"] == "document":
            await app.send_document(ADMIN_ID, order["receipt"]["file_id"], caption=text)
        else:
            await app.send_message(ADMIN_ID, text + "\n" + order["receipt"]["content"])

        await message.reply(
            f"سفارش شما ثبت شد.\n"
            f"کد رهگیری شما: {tracking_code}\n"
            "با تشکر از خرید شما!"
        )
        await message.reply("برای ثبت سفارش جدید از منوی اصلی استفاده کنید.", reply_markup=main_keyboard())

        app.user_data.pop(user_id, None)
        return

    await message.reply(
        "لطفاً از منوی اصلی یکی از دسته‌ها را انتخاب کنید.",
        reply_markup=main_keyboard()
    )

# --- اجرای ربات ---
app.run()
