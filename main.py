import os
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from telethon import TelegramClient
from telethon.sessions import StringSession

# Environment Variables (Heroku Config Vars)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
RAW_MUST_JOIN = os.environ.get("MUST_JOIN", "")  # Chahe link dalo, @ dalo, ya username dalo!

# Automatic Link & Username Sanitizer Function
def parse_channel_info(raw_input):
    if not raw_input or not raw_input.strip():
        return None, None
    raw_input = raw_input.strip()
    
    # Username nikalne ke liye processing
    if "t.me/" in raw_input:
        username = raw_input.rsplit("t.me/", 1)[-1].replace("@", "").strip("/")
    else:
        username = raw_input.replace("@", "").strip()
        
    # Valid Telegram URL banane ke liye logic
    if raw_input.startswith("http://") or raw_input.startswith("https://"):
        link = raw_input
    else:
        link = f"https://t.me/{username}"
        
    return username, link

CHANNEL_USERNAME, CHANNEL_LINK = parse_channel_info(RAW_MUST_JOIN)

app = Client("string_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary User Data Storage
USER_DATA = {}

# Channel Membership Verification
async def check_fsub(client, user_id):
    if not CHANNEL_USERNAME:
        return True
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["kicked", "banned"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

# /start Command Handler
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    user_first = message.from_user.first_name
    user_mention = f"<a href='tg://user?id={user_id}'>{user_first}</a>"

    if user_id in USER_DATA:
        USER_DATA.pop(user_id, None)

    # STRICT FORCE SUBSCRIBE CHECK
    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 Try Again / Verified", callback_data="check_join")]
        ])
        await message.reply_text(
            f"👋 <b>Welcome {user_mention}!</b>\n\n"
            "⛔ <b>Access Denied!</b>\n"
            "Bot ko use karne ke liye aapko humara official update channel join karna zaroori hai.\n\n"
            "👇 <i>Neeche button par click karke channel join karein aur fir 'Try Again' dabayein.</i>",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    await show_home_menu(message)

# Force Sub Try Again Callback
@app.on_callback_query(filters.regex("check_join"))
async def check_join_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await callback_query.answer("❌ Abhi tak join nahi kiya! Pehle channel join karo.", show_alert=True)
        return
    
    await callback_query.answer("✅ Channel Verified Successfully!")
    await show_home_menu(callback_query)

# Main Home Menu
async def show_home_menu(message_or_callback):
    user = message_or_callback.from_user if isinstance(message_or_callback, Message) else message_or_callback.from_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    updates_url = CHANNEL_LINK if CHANNEL_LINK else "https://t.me/Telegram"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Generate Session", callback_data="choose_session_type")],
        [
            InlineKeyboardButton("Help", callback_data="help_menu"),
            InlineKeyboardButton("Updates ↗", url=updates_url)
        ]
    ])
    text = (
        f"<b>☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆ STRING SESSION GENERATOR</b>\n\n"
        f"Welcome {user_mention}!\n\n"
        "Choose an option below to generate your session string."
    )
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@app.on_callback_query(filters.regex("home_back"))
async def home_back_callback(client, callback_query: CallbackQuery):
    USER_DATA.pop(callback_query.from_user.id, None)
    await callback_query.answer()
    await show_home_menu(callback_query)

# Help Menu Callback
@app.on_callback_query(filters.regex("help_menu"))
async def help_menu_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "📖 <b>Help & Instructions:</b>\n\n"
        "1. Click on <b>Generate Session</b>.\n"
        "2. Select your Session Type (Pyrogram / Telethon / Bot).\n"
        "3. Send your `API_ID` & `API_HASH` (or send /skip for default credentials).\n"
        "4. Enter Phone Number, OTP, and 2FA password.\n"
        "5. Get your Session String instantly!\n\n"
        "⚡ Powered by ☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="home_back")]])
    )

# Session Type Selection Screen
@app.on_callback_query(filters.regex("choose_session_type"))
async def session_type_menu(client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Pyrogram", callback_data="type_pyrogram"),
            InlineKeyboardButton("Pyrogram V2", callback_data="type_pyrogram_v2")
        ],
        [
            InlineKeyboardButton("Telethon", callback_data="type_telethon")
        ],
        [
            InlineKeyboardButton("Pyrogram Bot", callback_data="type_pyrogram_bot"),
            InlineKeyboardButton("Telethon Bot", callback_data="type_telethon_bot")
        ],
        [InlineKeyboardButton("Back", callback_data="home_back")]
    ])
    text = (
        "<b>Choose the Session Type</b>\n\n"
        "Select which type of string session you want to generate."
    )
    await callback_query.answer()
    await callback_query.message.edit_text(text, reply_markup=keyboard)

# Type Selected Handler
@app.on_callback_query(filters.regex("^type_"))
async def select_type_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    session_type = callback_query.data.replace("type_", "")
    
    type_display_map = {
        "pyrogram": "Pyrogram",
        "pyrogram_v2": "Pyrogram V2",
        "telethon": "Telethon",
        "pyrogram_bot": "Pyrogram Bot",
        "telethon_bot": "Telethon Bot"
    }
    
    display_name = type_display_map.get(session_type, session_type)
    
    USER_DATA[user_id] = {
        "session_type": session_type,
        "step": "api_id"
    }
    
    await callback_query.answer()
    await callback_query.message.reply_text(f"Starting <b>{display_name}</b> session generator...")
    await callback_query.message.reply_text(
        "Please send your <b>API_ID</b> to proceed.\n\n"
        "Send /skip to use the bot's default API credentials."
    )

# /skip Command Handler
@app.on_message(filters.command("skip") & filters.private)
async def skip_api_credentials(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_DATA:
        return

    USER_DATA[user_id]["api_id"] = API_ID
    USER_DATA[user_id]["api_hash"] = API_HASH
    
    stype = USER_DATA[user_id]["session_type"]
    if "bot" in stype:
        USER_DATA[user_id]["step"] = "bot_token"
        await message.reply_text("Please enter your <b>Bot Token</b>:")
    else:
        USER_DATA[user_id]["step"] = "phone"
        await message.reply_text("Please send your <b>Phone Number</b> with country code (e.g., `+919876543210`):")

# Text Inputs Handler (API ID, Hash, Phone, OTP, Password)
@app.on_message(filters.private & ~filters.command(["start", "skip"]))
async def handle_inputs(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_DATA:
        return

    data = USER_DATA[user_id]
    step = data.get("step")
    text = message.text.strip()

    # Step 1: API ID
    if step == "api_id":
        if not text.isdigit():
            await message.reply_text("❌ Invalid API ID. Please send numeric API ID or /skip:")
            return
        USER_DATA[user_id]["api_id"] = int(text)
        USER_DATA[user_id]["step"] = "api_hash"
        await message.reply_text("Now please send your <b>API_HASH</b>:")

    # Step 2: API Hash
    elif step == "api_hash":
        USER_DATA[user_id]["api_hash"] = text
        stype = data["session_type"]
        if "bot" in stype:
            USER_DATA[user_id]["step"] = "bot_token"
            await message.reply_text("Please enter your <b>Bot Token</b>:")
        else:
            USER_DATA[user_id]["step"] = "phone"
            await message.reply_text("Please send your <b>Phone Number</b> with country code (e.g., `+919876543210`):")

    # Step 3: Phone Number & Send OTP
    elif step == "phone":
        phone_number = text
        status_msg = await message.reply_text("🔄 Sending OTP...")
        
        curr_api_id = data["api_id"]
        curr_api_hash = data["api_hash"]
        stype = data["session_type"]

        try:
            if "telethon" in stype:
                t_client = TelegramClient(StringSession(), curr_api_id, curr_api_hash)
                await t_client.connect()
                res = await t_client.send_code_request(phone_number)
                USER_DATA[user_id].update({
                    "step": "otp",
                    "t_client": t_client,
                    "phone_number": phone_number,
                    "phone_code_hash": res.phone_code_hash
                })
            else:
                p_client = Client(f"p_{user_id}", api_id=curr_api_id, api_hash=curr_api_hash, in_memory=True)
                await p_client.connect()
                code_res = await p_client.send_code(phone_number)
                USER_DATA[user_id].update({
                    "step": "otp",
                    "p_client": p_client,
                    "phone_number": phone_number,
                    "phone_code_hash": code_res.phone_code_hash
                })

            await status_msg.edit_text(
                f"📨 OTP sent to `{phone_number}`!\n\n"
                "Please enter the OTP in this format: `1 2 3 4 5` (space separated)."
            )
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nSend /start to restart.")

    # Step 4: Verify OTP
    elif step == "otp":
        otp_code = text.replace(" ", "")
        stype = data["session_type"]
        status_msg = await message.reply_text("🔄 Verifying OTP...")

        try:
            if "telethon" in stype:
                t_client = data["t_client"]
                await t_client.sign_in(data["phone_number"], otp_code, phone_code_hash=data["phone_code_hash"])
                session_str = t_client.session.save()
                await t_client.disconnect()
            else:
                p_client = data["p_client"]
                await p_client.sign_in(data["phone_number"], data["phone_code_hash"], otp_code)
                session_str = await p_client.export_session_string()
                await p_client.disconnect()

            USER_DATA.pop(user_id, None)
            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            
            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated!</b>\n\n"
                f"👤 <b>For:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>\n\n"
                "⚠️ <i>Keep this string safe and do not share it with anyone!</i>",
                disable_web_page_preview=True
            )

        except SessionPasswordNeeded:
            USER_DATA[user_id]["step"] = "password"
            await status_msg.edit_text("🔒 2-Step Verification is enabled on your account. Please send your password:")
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Verification Failed:** `{str(e)}`\n\nSend /start to restart.")

    # Step 5: Password (2FA)
    elif step == "password":
        password = text
        stype = data["session_type"]
        status_msg = await message.reply_text("🔄 Verifying Password...")

        try:
            if "telethon" in stype:
                t_client = data["t_client"]
                await t_client.sign_in(password=password)
                session_str = t_client.session.save()
                await t_client.disconnect()
            else:
                p_client = data["p_client"]
                await p_client.check_password(password=password)
                session_str = await p_client.export_session_string()
                await p_client.disconnect()

            USER_DATA.pop(user_id, None)
            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated!</b>\n\n"
                f"👤 <b>For:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>\n\n"
                "⚠️ <i>Keep this string safe and do not share it with anyone!</i>",
                disable_web_page_preview=True
            )
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nSend /start to restart.")

    # Step 6: Bot Token Session Generation
    elif step == "bot_token":
        bot_tok = text
        stype = data["session_type"]
        status_msg = await message.reply_text("🔄 Generating Bot Session String...")

        try:
            curr_api_id = data["api_id"]
            curr_api_hash = data["api_hash"]

            if "telethon" in stype:
                t_client = TelegramClient(StringSession(), curr_api_id, curr_api_hash)
                await t_client.start(bot_token=bot_tok)
                session_str = t_client.session.save()
                await t_client.disconnect()
            else:
                p_client = Client(f"bot_{user_id}", api_id=curr_api_id, api_hash=curr_api_hash, bot_token=bot_tok, in_memory=True)
                await p_client.start()
                session_str = await p_client.export_session_string()
                await p_client.stop()

            USER_DATA.pop(user_id, None)
            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated!</b>\n\n"
                f"👤 <b>For:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>",
                disable_web_page_preview=True
            )
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nSend /start to restart.")

if __name__ == "__main__":
    print("Bot Started Successfully with Smart Link Parser!")
    app.run()
