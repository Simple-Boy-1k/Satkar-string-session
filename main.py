import os
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# Configuration from Environment Variables (Heroku Config Vars)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Force Subscribe Channel Username (Bina @ ke)
FSUBSCRIBE_CHANNEL = os.environ.get("FSUBSCRIBE_CHANNEL", "") 

app = Client("string_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User ki temporary states aur custom credentials store karne ke liye
USER_DATA = {}

async def check_fsub(client, user_id):
    if not FSUBSCRIBE_CHANNEL:
        return True
    try:
        await client.get_chat_member(FSUBSCRIBE_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    
    # Force Subscribe Check
    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FSUBSCRIBE_CHANNEL}")],
            [InlineKeyboardButton("🔄 Try Again / Joined", callback_data="check_join")]
        ])
        await message.reply_text(
            "⛔ **Access Denied:**\nKya Yrr😆 Channel Join Nahi Kiya Hai Tu😝.",
            reply_markup=keyboard
        )
        return

    await show_home_menu(message)

async def show_home_menu(message_or_callback):
    user = message_or_callback.from_user if isinstance(message_or_callback, Message) else message_or_callback.from_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Generate Session", callback_data="gen_session_menu")],
        [
            InlineKeyboardButton("Help", callback_data="help_menu"),
            InlineKeyboardButton("Updates ↗", url=f"https://t.me/{FSUBSCRIBE_CHANNEL}" if FSUBSCRIBE_CHANNEL else "https://t.me/Telegram")
        ]
    ])
    text = (
        f"<b>☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆ SESSION GENERATOR</b>\n\n"
        f"👋 Welcome, {user_mention}!\n\n"
        "Choose an option below to generate your session string.\n\n"
        "🟢 <b>DEVELOPER / BRANDING</b>: (☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆ | RDX | SK)\n"
        "नॉक्स भाई और उनके दोस्त को चोर के साबकी माकी Chu*😂"
    )
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@app.on_callback_query(filters.regex("check_join"))
async def check_join_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    is_joined = await check_fsub(client, user_id)
    if not is_joined:
        await callback_query.answer("❌ Aapne abhi tak channel join nahi kiya hai!", show_alert=True)
        return
    await callback_query.answer("✅ Verified!")
    await show_home_menu(callback_query)

@app.on_callback_query(filters.regex("home_back"))
async def home_back_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    USER_DATA.pop(user_id, None)
    await callback_query.answer()
    await show_home_menu(callback_query)

@app.on_callback_query(filters.regex("help_menu"))
async def help_menu_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "📖 **Help & Instructions:**\n\n"
        "1. Click on **Generate Session**.\n"
        "2. Choose between **Generate via Bot** or **Generate via Tools**.\n"
        "3. Provide your `API_ID`, `API_HASH`, and Phone Number.\n"
        "4. Enter OTP and 2FA Password to get your session string securely!\n\n"
        "⚡ Powered by ☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="home_back")]])
    )

@app.on_callback_query(filters.regex("gen_session_menu"))
async def gen_session_menu_callback(client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Generate via Bot", callback_data="method_bot"),
            InlineKeyboardButton("Generate via Tools", callback_data="method_tools")
        ],
        [InlineKeyboardButton("« Back", callback_data="home_back")]
    ])
    text = (
        "<b>Select a Method</b>\n\n"
        "Choose how you would like to generate your session string.\n\n"
        "<b>Note:</b> The Telegram Tools method is recommended for the most reliable results.\n"
        "<b>Warning:</b> The Bot method may cause your account to be logged out automatically.\n\n"
        "⚡ ☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆ MODS"
    )
    await callback_query.answer()
    await callback_query.message.edit_text(text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("^method_"))
async def method_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    method = callback_query.data.split("_")[1]
    
    USER_DATA[user_id] = {"method": method, "step": "api_id"}
    
    await callback_query.answer()
    await callback_query.message.edit_text(
        "🔑 **Enter API ID**\n\n"
        "Apni Telegram API ID enter karein (my.telegram.org se prapt karein):\n"
        "🌐 Website: https://my.telegram.org\n\n"
        "⚡ <b>☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆ MODS</b>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="gen_session_menu")]])
    )

@app.on_message(filters.private & ~filters.command(["start"]))
async def handle_user_input(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_DATA:
        return

    data = USER_DATA[user_id]
    user_state = data.get("step")
    text = message.text.strip()

    # Step 1: API ID Lena
    if user_state == "api_id":
        if not text.isdigit():
            await message.reply_text("❌ API ID sirf numbers me honi chahiye. Dobara enter karein:")
            return
        
        USER_DATA[user_id]["api_id"] = int(text)
        USER_DATA[user_id]["step"] = "api_hash"
        await message.delete()
        await message.reply_text("🔐 **Enter API HASH**\n\nApni Telegram API Hash enter karein:")

    # Step 2: API Hash Lena
    elif user_state == "api_hash":
        USER_DATA[user_id]["api_hash"] = text
        USER_DATA[user_id]["step"] = "phone"
        await message.delete()
        await message.reply_text(
            "📱 **Phone Number Required**\n\n"
            "Kripya apna Telegram account ka phone number country code ke sath bhejein (Jaise: `+919876543210`):"
        )

    # Step 3: Phone Number & Send OTP
    elif user_state == "phone":
        phone_number = text
        await message.delete()
        
        status_msg = await message.reply_text("🔄 Connecting with your API credentials & sending OTP...")
        
        try:
            custom_api_id = data["api_id"]
            custom_api_hash = data["api_hash"]
            
            temp_client = Client(f"session_{user_id}", api_id=custom_api_id, api_hash=custom_api_hash, in_memory=True)
            await temp_client.connect()
            
            sent_code = await temp_client.send_code(phone_number)
            
            USER_DATA[user_id].update({
                "step": "otp",
                "temp_client": temp_client,
                "phone_number": phone_number,
                "phone_code_hash": sent_code.phone_code_hash,
                "status_msg_id": status_msg.id
            })
            
            await status_msg.edit_text(
                f"📨 **OTP Sent Successfully!**\n\n"
                f"Aapke number `{phone_number}` par Telegram par OTP gaya hoga.\n"
                f"Kripya OTP bhejein (Jaise: `1 2 3 4 5`):"
            )
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nDobara /start dabayein.")

    # Step 4: Verify OTP
    elif user_state == "otp":
        otp_code = text.replace(" ", "")
        temp_client = data["temp_client"]
        phone_number = data["phone_number"]
        phone_code_hash = data["phone_code_hash"]
        
        await message.delete()
        status_msg = await message.reply_text("🔄 Verifying OTP...")

        try:
            await temp_client.sign_in(phone_number, phone_code_hash, otp_code)
            
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            
            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            await status_msg.edit_text(
                "✅ **Session Generated Successfully!**\n\n"
                f"👤 **Generated For:** {user_mention}\n\n"
                f"Your Pyrogram V2 Session String:\n`{string_session}`\n\n"
                "⚠️ *Isko kisi ke sath share na karein!* — By ☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Main Menu", callback_data="home_back")]]),
                disable_web_page_preview=True
            )
            
        except SessionPasswordNeeded:
            USER_DATA[user_id]["step"] = "password"
            await status_msg.edit_text(
                "🔒 **2-Step Verification Enabled**\n\n"
                "Aapke account par 2FA password laga hai. Kripya apna Cloud Password yahan send karein:"
            )
        except Exception as e:
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Verification Failed:** `{str(e)}`\n\nDobara /start dabayein.")

    # Step 5: Verify 2FA Password
    elif user_state == "password":
        password = text
        temp_client = data["temp_client"]
        
        await message.delete()
        status_msg = await message.reply_text("🔄 Verifying Password...")

        try:
            await temp_client.check_password(password=password)
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            
            user_mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            await status_msg.edit_text(
                "✅ **Session Generated Successfully!**\n\n"
                f"👤 **Generated For:** {user_mention}\n\n"
                f"Your Pyrogram V2 Session String:\n`{string_session}`\n\n"
                "⚠️ *Isko kisi ke sath share na karein!* — By ☆𝙎𝘼𝙍𝙆𝘼𝙍 メ 𝙉𝙊𝙓☆",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Main Menu", callback_data="home_back")]]),
                disable_web_page_preview=True
            )
        except Exception as e:
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Wrong Password / Error:** `{str(e)}`\n\nDobara /start dabayein.")

if __name__ == "__main__":
    print("Sarkar_x_Nox_String_Bot is fully Started✅")
    app.run()
