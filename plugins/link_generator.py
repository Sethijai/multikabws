# link_generator.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from asyncio import TimeoutError
from helper_func import encode, get_message_id, encode_link, decode_link
from config import *
from database.database import get_bot

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('batch'))
async def batch(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes) or send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: Failed to receive the first message. {str(e)}", quote=True)
            return
        f_channel_id, f_msg_id = await get_message_id(client, first_message)
        if f_channel_id == db_channel and f_msg_id:
            break
        else:
            await first_message.reply_text(
                "❌ Error: This is not a valid forwarded post or link from the bot's DB Channel.",
                quote=True
            )

    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from DB Channel (with Quotes) or send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: Failed to receive the second message. {str(e)}", quote=True)
            return
        s_channel_id, s_msg_id = await get_message_id(client, second_message)
        if s_channel_id == db_channel and s_msg_id:
            if s_msg_id >= f_msg_id:
                break
            else:
                await second_message.reply_text(
                    "❌ Error: The last message ID must be greater than or equal to the first message ID.",
                    quote=True
                )
        else:
            await second_message.reply_text(
                "❌ Error: This is not a valid forwarded post or link from the bot's DB Channel.",
                quote=True
            )

    try:
        link = await encode_link(f_msg_id=f_msg_id, s_msg_id=s_msg_id, channel_id=db_channel)
        print(f"Generated batch link: {link}")
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        await second_message.reply_text(
            f"<b>Here is your batch link</b>\n\nhttps://t.me/{client.username}?start={link}",
            quote=True,
            reply_markup=reply_markup
        )
    except ValueError as e:
        await second_message.reply_text(f"❌ Error generating link: {str(e)}", quote=True)
    except Exception as e:
        await second_message.reply_text(f"❌ Unexpected error: {str(e)}", quote=True)

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    while True:
        try:
            channel_message = await client.ask(
                text="Forward Message from the DB Channel (with Quotes)..\nor Send the DB Channel Post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        channel_id, msg_id = await get_message_id(client, channel_message)
        if channel_id == db_channel and msg_id:
            break
        else:
            await channel_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is not taken from DB Channel", quote=True)
            continue

    link = await encode_link(f_msg_id=msg_id, channel_id=db_channel)
    print(f"Generated single link: {link}")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("custom_batch"))
async def custom_batch(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    collected = []
    STOP_KEYBOARD = ReplyKeyboardMarkup([["STOP"]], resize_keyboard=True)

    await message.reply("Send all messages you want to include in batch.\n\nPress STOP when you're done.", reply_markup=STOP_KEYBOARD)

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="Waiting for files/messages...\nPress STOP to finish.",
                timeout=60
            )
        except asyncio.TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "STOP":
            break

        try:
            sent = await user_msg.copy(db_channel, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
            continue

    await message.reply("✅ Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("❌ No messages were added to batch.")
        return

    link = await encode_link(f_msg_id=collected[0], s_msg_id=collected[-1], channel_id=db_channel)
    print(f"Generated custom batch link: {link}")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await message.reply(f"<b>Here is your custom batch link:</b>\n\n{link}", reply_markup=reply_markup)

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('nbatch'))
async def new_batch(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    db_channel = bot_settings.get('database_channel', CHANNEL_ID)

    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        f_channel_id, f_msg_id = await get_message_id(client, first_message)
        if f_channel_id == db_channel and f_msg_id:
            break
        else:
            await first_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote=True)
            continue

    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from DB Channel (with Quotes)..\nor Send the DB Channel Post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        s_channel_id, s_msg_id = await get_message_id(client, second_message)
        if s_channel_id == db_channel and s_msg_id:
            break
        else:
            await second_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote=True)
            continue

    link = await encode_link(f_msg_id=f_msg_id, s_msg_id=s_msg_id, channel_id=db_channel)
    print(f"Generated new batch link: {link}")
    if WEBSITE_URL_MODE:
        base64_string = link.split("start=")[1]
        link = f"{WEBSITE_URL}?HACKHEIST={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Here is your new batch link</b>\n\n<code>{link}</code>", quote=True, reply_markup=reply_markup)
