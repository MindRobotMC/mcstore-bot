import os
import json
import random
import string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- محیط ---
def get_env_int(key): val = os.getenv(key); return int(val) if val else exit(f"{key} تعریف نشده")
def get_env_str(key): val = os.getenv(key); return val if val else exit(f"{key} تعریف نشده")

API_ID = get_env_int("API_ID")
API_HASH = get_env_str("API_HASH")
BOT_TOKEN = get_env_str("BOT_TOKEN")
ADMIN_ID = get_env_int("ADMIN_ID")
CHANNEL_USERNAME = get_env_str("CHANNEL_USERNAME")
channel_short = CHANNEL_USERNAME[1:] if CHANNEL_USERNAME.startswith("@") else CHANNEL_USERNAME

# --- ربات ---
app = Client("mcstore_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app.user_data = {}

# --- سفارشات ---
try:
    with open("orders.json", "r", encoding="utf-8") as f:
        orders = json.load(f)
except:
    orders = []

# --- منو ---
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ ثبت سفارش جدید", callback_data="order")],
        [InlineKeyboardButton("📋 سفارشات من", callback_data="my_orders")],
        [InlineKeyboardButton("🧾 احراز هویت", callback_data="verify")],
        [InlineKeyboardButton("👤 پروفایل من", callback_data="profile")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ])

# --- کد رهگیری ---
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# --- استارت با جوین ---
@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    user = message.from_user
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ("left", "kicked"):
            raise Exception()
    except:
        await message.reply(
            "📢 برای استفاده از ربات باید در کانال زیر عضو باشید:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔗 عضویت", url=f"https://t.me/{channel_short}")]]
            )
        )
        return

    await message.reply(
        f"سلام {user.first_name} عزیز 👋\n"
        "به ربات خدمات MC-STORE خوش اومدی.\nاز منوی زیر استفاده کن 👇",
        reply_markup=main_menu()
    )

# --- دکمه‌ها ---
@app.on_callback_query()
async def callback(client, query):
    data = query.data
    user = query.from_user
    user_id = user.id

    if data == "order":
        app.user_data[user_id] = {"step": "waiting_order_text"}
        await query.message.edit("📝 لطفاً توضیح سفارش خود را ارسال کنید:", reply_markup=main_menu())

    elif data == "my_orders":
        user_orders = [o for o in orders if o["user_id"] == user_id]
        if not user_orders:
            text = "📭 سفارشی ثبت نکردید."
        else:
            text = "📋 سفارشات شما:\n\n"
            for o in user_orders[-5:]:
                text += f"🔹 کد: {o['tracking_code']}\n📝 {o['order_text'][:50]}...\n\n"
        await query.message.edit(text, reply_markup=main_menu())

    elif data == "verify":
        app.user_data[user_id] = {"step": "waiting_verification"}
        await query.message.edit("🆔 لطفاً تصویر کارت ملی یا هویت خود را ارسال کنید:", reply_markup=main_menu())

    elif data == "profile":
        await query.message.edit(
            f"👤 پروفایل شما:\n\n"
            f"نام: {user.first_name}\n"
            f"یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
            f"آی‌دی عددی: {user.id}",
            reply_markup=main_menu()
        )

    elif data == "support":
        await query.message.edit(
            "📞 برای پشتیبانی به آیدی زیر پیام بده:\n\n"
            "@MindRobotMC",
            reply_markup=main_menu()
        )

    await query.answer()

# --- پیام‌ها ---
@app.on_message(filters.private & ~filters.command("start"))
async def handle_message(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username or "ندارد"
    state = app.user_data.get(user_id, {})

    # --- احراز هویت ---
    if state.get("step") == "waiting_verification":
        if message.photo or message.document:
            await message.reply("✅ ارسال شد. منتظر بررسی ادمین باشید.", reply_markup=main_menu())
            if message.photo:
                await app.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"احراز هویت از {user_id}")
            else:
                await app.send_document(ADMIN_ID, message.document.file_id, caption=f"احراز هویت از {user_id}")
        else:
            await message.reply("⚠️ لطفاً فقط عکس یا سند ارسال کنید.")
        app.user_data.pop(user_id, None)
        return

    # --- سفارش ---
    if state.get("step") == "waiting_order_text":
        app.user_data[user_id]["order_text"] = message.text
        app.user_data[user_id]["step"] = "waiting_order_receipt"
        await message.reply("📤 لطفاً تصویر یا شماره رسید پرداخت را ارسال کنید.")
        return

    if state.get("step") == "waiting_order_receipt":
        order_text = app.user_data[user_id].get("order_text", "")
        tracking_code = generate_code()
        receipt = None

        if message.photo:
            receipt = {"type": "photo", "file_id": message.photo[-1].file_id}
        elif message.document:
            receipt = {"type": "document", "file_id": message.document.file_id}
        elif message.text:
            receipt = {"type": "text", "content": message.text}
        else:
            await message.reply("⚠️ فقط عکس، سند یا متن قابل قبول است.")
            return

        order = {
            "user_id": user_id,
            "user_name": user_name,
            "user_username": username,
            "order_text": order_text,
            "receipt": receipt,
            "tracking_code": tracking_code
        }
        orders.append(order)
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

        caption = (
            f"📥 سفارش جدید:\n"
            f"👤 {user_name} (@{username})\n"
            f"📝 {order_text}\n"
            f"🔑 کد رهگیری: {tracking_code}"
        )
        if receipt["type"] == "photo":
            await app.send_photo(ADMIN_ID, receipt["file_id"], caption=caption)
        elif receipt["type"] == "document":
            await app.send_document(ADMIN_ID, receipt["file_id"], caption=caption)
        else:
            await app.send_message(ADMIN_ID, caption + "\n🧾 " + receipt["content"])

        await message.reply(f"✅ سفارش شما با کد رهگیری `{tracking_code}` ثبت شد.", reply_markup=main_menu())
        app.user_data.pop(user_id, None)
        return

    await message.reply("❗ لطفاً از منوی اصلی یکی از گزینه‌ها را انتخاب کنید.", reply_markup=main_menu())

# --- اجرا ---
app.run()
