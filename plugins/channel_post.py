# channel_post.py
import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from bot import Bot
from config import *
from helper_func import encode
from database.database import get_bot

@Bot.on_message(filters.private & filters.user(ADMINS) & ~filters.command(['start', 'users', 'broadcast', 'batch', 'genlink', 'stats', 'clone_bot', 'force_sub_channel', 'auto_delete', 'individual_auto_delete', 'database_channel_id', 'protect_content']))
async def channel_post(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    reply_text = await message.reply_text("Please Wait...!", quote=True)
    try:
        post_message = await message.copy(chat_id=db_channel, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id=db_channel, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went Wrong..!")
        return
    converted_id = post_message.id * abs(int(db_channel))
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Here is your link</b>\n\n<code>{link}</code>", reply_markup=reply_markup, disable_web_page_preview=True)

    if not DISABLE_CHANNEL_BUTTON:
        await post_message.edit_reply_markup(reply_markup)

@Bot.on_message(filters.channel & filters.incoming & filters.chat(lambda _, __, m: m.chat.id == int((get_bot(_.TG_BOT_TOKEN) or {}).get('database_channel', CHANNEL_ID))))
async def new_post(client: Client, message: Message):
    if DISABLE_CHANNEL_BUTTON:
        return

    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    converted_id = message.id * abs(int(db_channel))
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)
        pass
