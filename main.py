import os
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, PhoneNumberInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# Configuration (Aap environment variables ya direct values yahan daal sakte hain)
API_ID = int(os.environ.get("API_ID", "31551910"))  # Apni my.telegram.org wali API_ID dalein
API_HASH = os.environ.get("API_HASH", "c2e8e7946d5e4ea947d44b674008f33e")  # Apni API_HASH dalein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8540979538:AAGPRvHt5e-l7wTQbeX4l_pcX7JYr6B910w")  # BotFather wala Token dalein

app = Client("string_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User ki temporary states store karne ke liye dictionary
USER_DATA = {}

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Generate String Session", callback_data="gen_session")]
    ])
    await message.reply_text(
        "👋 **Welcome to Pyrogram String Session Generator Bot!**\n\n"
        "Apne Telegram account ka Pyrogram V2 session string banane ke liye niche diye gaye button par click karein.",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("gen_session"))
async def gen_session_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    USER_DATA[user_id] = {"step": "phone"}
    
    await callback_query.answer()
    await callback_query.message.edit_text(
        "📱 **Phone Number Required**\n\n"
        "Kripya apne Telegram account ka phone number country code ke sath bhejein (Jaise: `+919876543210`):"
    )

@app.on_message(filters.private & ~filters.command(["start"]))
async def handle_user_input(client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_DATA:
        return

    user_state = USER_DATA[user_id].get("step")
    text = message.text.strip()

    # Step 1: Phone Number Handle Karna
    if user_state == "phone":
        phone_number = text
        await message.delete()  # Security ke liye phone number delete kar dena behtar hai
        
        status_msg = await message.reply_text("🔄 Connecting to Telegram & sending OTP...")
        
        try:
            # Temporary client client-side generation ke liye
            temp_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            
            sent_code = await temp_client.send_code(phone_number)
            
            USER_DATA[user_id] = {
                "step": "otp",
                "temp_client": temp_client,
                "phone_number": phone_number,
                "phone_code_hash": sent_code.phone_code_hash,
                "status_msg_id": status_msg.id
            }
            
            await status_msg.edit_text(
                f"📨 **OTP Sent Successfully!**\n\n"
                f"Aapke number `{phone_number}` par Telegram official app par ek OTP aaya hoga.\n"
                f"Kripya OTP bhejein (Agar space ke sath ho toh space dekar likhein, jaise: `1 2 3 4 5`):"
            )
        except Exception as e:
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`\n\nDobara /start dabayein.")

    # Step 2: OTP Handle Karna
    elif user_state == "otp":
        otp_code = text.replace(" ", "")
        data = USER_DATA[user_id]
        temp_client = data["temp_client"]
        phone_number = data["phone_number"]
        phone_code_hash = data["phone_code_hash"]
        
        await message.delete()
        status_msg = await message.reply_text("🔄 Verifying OTP...")

        try:
            await temp_client.sign_in(phone_number, phone_code_hash, otp_code)
            
            # Agar 2FA password nahi hai toh yahin session ban jayega
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            
            await status_msg.edit_text(
                "✅ **Session Generated Successfully!**\n\n"
                f"Your Pyrogram V2 Session String:\n`{string_session}`\n\n"
                "⚠️ *Isko kisi ke sath share na karein!*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Create Another", callback_data="gen_session")]])
            )
            
        except SessionPasswordNeeded:
            # Step 3: Agar Two-Step Verification (Cloud Password) laga hai
            USER_DATA[user_id]["step"] = "password"
            await status_msg.edit_text(
                "🔒 **2-Step Verification Enabled**\n\n"
                "Aapke account par 2FA password laga hai. Kripya apna Cloud Password yahan send karein:"
            )
        except Exception as e:
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Verification Failed:** `{str(e)}`\n\nDobara /start dabayein.")

    # Step 3: Password Handle Karna
    elif user_state == "password":
        password = text
        data = USER_DATA[user_id]
        temp_client = data["temp_client"]
        
        await message.delete()
        status_msg = await message.reply_text("🔄 Verifying Password...")

        try:
            await temp_client.check_password(password=password)
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            
            await status_msg.edit_text(
                "✅ **Session Generated Successfully!**\n\n"
                f"Your Pyrogram V2 Session String:\n`{string_session}`\n\n"
                "⚠️ *Isko kisi ke sath share na karein!*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Create Another", callback_data="gen_session")]])
            )
        except Exception as e:
            await temp_client.disconnect()
            USER_DATA.pop(user_id, None)
            await status_msg.edit_text(f"❌ **Wrong Password / Error:** `{str(e)}`\n\nDobara /start dabayein.")

if __name__ == "__main__":
    print("String Generator Bot is starting...")
    app.run()
