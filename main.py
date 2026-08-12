import os
import time
import struct
import base64
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import SessionPasswordNeeded, UserNotParticipant, ChatAdminRequired, ChannelInvalid, PeerIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from telethon import TelegramClient
from telethon.sessions import StringSession

# Environment Variables
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# Channel Force Sub Configs
RAW_MUST_JOIN = os.environ.get("MUST_JOIN", "").strip()
RAW_MUST_JOIN_LINK = os.environ.get("MUST_JOIN_LINK", "").strip()

# Custom Brand Name Config
BRAND_NAME = os.environ.get("BRAND_NAME", "𝐒𝐀𝐑𝐊𝐀𝐑").strip()

def setup_force_sub():
    chat_target = None
    link_target = "https://t.me/Telegram"

    if RAW_MUST_JOIN:
        if RAW_MUST_JOIN.startswith("-100") or RAW_MUST_JOIN.lstrip("-").isdigit():
            chat_target = int(RAW_MUST_JOIN)
        else:
            chat_target = RAW_MUST_JOIN.replace("@", "").replace("https://t.me/", "").replace("t.me/", "").strip()

    if RAW_MUST_JOIN_LINK:
        if not RAW_MUST_JOIN_LINK.startswith(("http://", "https://")):
            link_target = f"https://{RAW_MUST_JOIN_LINK}"
        else:
            link_target = RAW_MUST_JOIN_LINK
    elif isinstance(chat_target, str) and chat_target:
        link_target = f"https://t.me/{chat_target}"

    return chat_target, link_target

FSUB_CHAT, FSUB_LINK = setup_force_sub()

app = Client("string_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

USER_DATA = {}

# Strict Session Data Wipe & Force Disconnect
async def clean_user_session(user_id: int):
    if user_id in USER_DATA:
        data = USER_DATA.get(user_id, {})
        sess_name = data.get("sess_name")
        
        # Disconnect Pyrogram Client
        if "p_client" in data and data["p_client"]:
            try:
                await data["p_client"].stop()
            except Exception:
                try:
                    await data["p_client"].disconnect()
                except Exception:
                    pass

        # Disconnect Telethon Client
        if "t_client" in data and data["t_client"]:
            try:
                await data["t_client"].disconnect()
            except Exception:
                pass

        # Delete any temporary session file
        if sess_name:
            for ext in [".session", ".session-journal"]:
                if os.path.exists(f"{sess_name}{ext}"):
                    try:
                        os.remove(f"{sess_name}{ext}")
                    except Exception:
                        pass

        USER_DATA.pop(user_id, None)

# Custom Pyrogram V1 String Exporter (Fixes 271 bytes error strictly)
async def get_pyrogram_v1_string(p_client: Client) -> str:
    try:
        me = await p_client.get_me()
        dc_id = await p_client.storage.dc_id()
        test_mode = await p_client.storage.test_mode()
        auth_key = await p_client.storage.auth_key()
        
        # Pyrogram V1 struct format: >B?256sI? (263 bytes)
        packed = struct.pack(
            ">B?256sI?",
            dc_id,
            test_mode,
            auth_key,
            me.id & 0xFFFFFFFF,  # uint32 trunc
            me.is_bot
        )
        return base64.urlsafe_b64encode(packed).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Pyrogram V1 conversion fallback: {e}")
        return await p_client.export_session_string()

# Force Subscribe Verification Check
async def check_fsub(client: Client, user_id: int) -> bool:
    if not FSUB_CHAT or (OWNER_ID and user_id == OWNER_ID):
        return True

    try:
        member = await client.get_chat_member(FSUB_CHAT, user_id)
        if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.RESTRICTED]:
            return False
        return True
    except UserNotParticipant:
        return False
    except (ChatAdminRequired, ChannelInvalid, PeerIdInvalid) as e:
        print(f"⚠️ FSUB CONFIG ERROR: {e}")
        return True
    except Exception as e:
        print(f"⚠️ FSUB ERROR: {e}")
        return False

# Join Channel Keyboard
def get_fsub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Official Channel", url=FSUB_LINK)],
        [InlineKeyboardButton("🔄 Try Again / Verified", callback_data="check_join")]
    ])

# /start Command Handler
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_first = message.from_user.first_name
    user_mention = f"<a href='tg://user?id={user_id}'>{user_first}</a>"

    await clean_user_session(user_id)

    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await message.reply_text(
            f"👋 <b>Welcome {user_mention}!</b>\n\n"
            f"⛔ <b>Access Denied!</b>\n"
            f"Bot ka use karne ke liye pehle humara official channel join karein.\n\n"
            f"👑 <b>Brand:</b> {BRAND_NAME}\n\n"
            f"👇 <i>Neeche Join Button par click karke channel join karein aur fir 'Try Again / Verified' dabayein.</i>",
            reply_markup=get_fsub_keyboard(),
            disable_web_page_preview=True
        )
        return

    await show_home_menu(message)

# Force Sub Callback
@app.on_callback_query(filters.regex("check_join"))
async def check_join_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await callback_query.answer("❌ Aapne abhi tak channel join nahi kiya hai! Pehle join karein.", show_alert=True)
        return
    
    await callback_query.answer("✅ Verification Successful!")
    await show_home_menu(callback_query)

# /generate Command Handler
@app.on_message(filters.command("generate") & filters.private)
async def generate_command(client: Client, message: Message):
    user_id = message.from_user.id
    await clean_user_session(user_id)

    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await message.reply_text(
            f"⛔ <b>Access Denied!</b> Pehle channel join karein.",
            reply_markup=get_fsub_keyboard(),
            disable_web_page_preview=True
        )
        return

    await send_session_menu(message)

# Home Main Menu Screen
async def show_home_menu(message_or_callback):
    user = message_or_callback.from_user if isinstance(message_or_callback, Message) else message_or_callback.from_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Generate Session", callback_data="choose_session_type")],
        [
            InlineKeyboardButton("📖 Help", callback_data="help_menu"),
            InlineKeyboardButton("📢 Updates ↗", url=FSUB_LINK)
        ]
    ])
    
    text = (
        f"👑 <b>{BRAND_NAME} STRING SESSION GENERATOR</b> 👑\n\n"
        f"👋 Welcome {user_mention}!\n\n"
        f"Select an option below to generate your string session safely and fast.\n\n"
        f"⚡ <b>POWERED BY:</b> {BRAND_NAME}"
    )
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

async def send_session_menu(message_or_callback):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Pyrogram (V1 - Bot Compatible)", callback_data="type_pyrogram"),
            InlineKeyboardButton("Pyrogram V2", callback_data="type_pyrogram_v2")
        ],
        [
            InlineKeyboardButton("Telethon", callback_data="type_telethon")
        ],
        [
            InlineKeyboardButton("Pyrogram Bot", callback_data="type_pyrogram_bot"),
            InlineKeyboardButton("Telethon Bot", callback_data="type_telethon_bot")
        ],
        [InlineKeyboardButton("« Back", callback_data="home_back")]
    ])
    text = "⚙️ <b>Select Session Type</b>\n\nChoose which string session protocol you want to generate."
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("home_back"))
async def home_back_callback(client: Client, callback_query: CallbackQuery):
    await clean_user_session(callback_query.from_user.id)
    await callback_query.answer()
    await show_home_menu(callback_query)

# Help Menu
@app.on_callback_query(filters.regex("help_menu"))
async def help_menu_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        f"📖 <b>Instructions & Help:</b>\n\n"
        f"1. Click on <b>Generate Session</b> or send /generate.\n"
        f"2. Select <b>Pyrogram (V1)</b> for Userbots.\n"
        f"3. Send your `API_ID` & `API_HASH` (or send /skip for default credentials).\n"
        f"4. Send Phone Number, OTP, and 2FA password.\n"
        f"5. Receive your Session instantly!\n\n"
        f"⚡ <b>Brand:</b> {BRAND_NAME}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="home_back")]]),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("choose_session_type"))
async def session_type_menu_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await callback_query.answer("❌ Pehle official channel join karein!", show_alert=True)
        return

    await callback_query.answer()
    await send_session_menu(callback_query)

# Type Selected Handler
@app.on_callback_query(filters.regex("^type_"))
async def select_type_handler(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await callback_query.answer("❌ Pehle official channel join karein!", show_alert=True)
        return

    # Flush old connections completely
    await clean_user_session(user_id)

    session_type = callback_query.data.replace("type_", "")
    sess_name = f"sess_{user_id}_{time.time_ns()}"

    USER_DATA[user_id] = {
        "session_type": session_type,
        "step": "api_id",
        "sess_name": sess_name
    }
    
    await callback_query.answer()
    await callback_query.message.reply_text(f"🚀 Starting <b>{session_type.upper()}</b> generator...")
    await callback_query.message.reply_text(
        "Please send your <b>API_ID</b> to proceed.\n\n"
        "Send /skip to use default API credentials."
    )

# /skip Command Handler
@app.on_message(filters.command("skip") & filters.private)
async def skip_api_credentials(client: Client, message: Message):
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

# Input Handler
@app.on_message(filters.private & ~filters.command(["start", "generate", "skip"]))
async def handle_inputs(client: Client, message: Message):
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
        phone_number = text.replace(" ", "")
        status_msg = await message.reply_text("🔄 Sending OTP...")
        
        curr_api_id = data["api_id"]
        curr_api_hash = data["api_hash"]
        stype = data["session_type"]
        sess_name = data["sess_name"]

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
                p_client = Client(sess_name, api_id=curr_api_id, api_hash=curr_api_hash, in_memory=True)
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
                "Please enter OTP in this format: `1 2 3 4 5` (space separated)."
            )
        except Exception as e:
            await clean_user_session(user_id)
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
            else:
                p_client = data["p_client"]
                await p_client.sign_in(data["phone_number"], data["phone_code_hash"], otp_code)
                if stype == "pyrogram":
                    session_str = await get_pyrogram_v1_string(p_client)
                else:
                    session_str = await p_client.export_session_string()

            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            
            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated Successfully!</b>\n\n"
                f"👤 <b>User:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>\n\n"
                f"⚡ <i>Powered by {BRAND_NAME}</i>",
                disable_web_page_preview=True
            )
            await clean_user_session(user_id)

        except SessionPasswordNeeded:
            USER_DATA[user_id]["step"] = "password"
            await status_msg.edit_text("🔒 2-Step Verification is enabled. Please send your 2FA password:")
        except Exception as e:
            await clean_user_session(user_id)
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
            else:
                p_client = data["p_client"]
                await p_client.check_password(password=password)
                if stype == "pyrogram":
                    session_str = await get_pyrogram_v1_string(p_client)
                else:
                    session_str = await p_client.export_session_string()

            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated Successfully!</b>\n\n"
                f"👤 <b>User:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>\n\n"
                f"⚡ <i>Powered by {BRAND_NAME}</i>",
                disable_web_page_preview=True
            )
            await clean_user_session(user_id)

        except Exception as e:
            await clean_user_session(user_id)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nSend /start to restart.")

    # Step 6: Bot Session Generation
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
                p_client = Client(f"bot_{user_id}_{time.time_ns()}", api_id=curr_api_id, api_hash=curr_api_hash, bot_token=bot_tok, in_memory=True)
                await p_client.start()
                if stype == "pyrogram_bot":
                    session_str = await get_pyrogram_v1_string(p_client)
                else:
                    session_str = await p_client.export_session_string()
                await p_client.stop()

            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

            await status_msg.edit_text(
                f"✅ <b>{stype.upper()} Session Generated!</b>\n\n"
                f"👤 <b>User:</b> {user_mention}\n\n"
                f"<code>{session_str}</code>\n\n"
                f"⚡ <i>Powered by {BRAND_NAME}</i>",
                disable_web_page_preview=True
            )
            await clean_user_session(user_id)

        except Exception as e:
            await clean_user_session(user_id)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nSend /start to restart.")

if __name__ == "__main__":
    print(f"Bot Started Successfully with {BRAND_NAME} Branding!")
    app.run()
