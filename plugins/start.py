# start.py
import random
import os
import asyncio
import humanize
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, BadRequest
from bot import Bot
from config import *
from helper_func import subscribed, encode_link, decode_link, get_messages
from database.database import add_user, del_user, full_userbase, present_user, add_bot, get_bot, update_bot_settings, is_bot_creator_or_admin, set_session_data, get_session_data, clear_session_data

async def delete_files(codeflix_msgs, client, message, delete_time=None):
    """Delete messages after the specified time."""
    if not codeflix_msgs:
        return
    
    if delete_time is None:
        delete_time = FILE_AUTO_DELETE
    
    await asyncio.sleep(delete_time)
    
    message_ids = [msg.id for msg in codeflix_msgs]
    try:
        await client.delete_messages(chat_id=message.chat.id, message_ids=message_ids)
        print(f"Deleted {len(message_ids)} messages for user {message.chat.id}")
    except Exception as e:
        print(f"Failed to delete messages for user {message.chat.id}: {e}")

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if not await present_user(id):
        try:
            await add_user(id)
        except Exception as e:
            print(f"Error adding user: {e}")
            pass
    
    text = message.text
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    protect_content = bot_settings.get('protect_content', PROTECT_CONTENT)
    bulk_delete_timer = bot_settings.get('bulk_delete_timer', FILE_AUTO_DELETE)
    individual_delete_timer = bot_settings.get('individual_delete_timer', INDIVIDUAL_AUTO_DELETE)
    database_channel = bot_settings.get('database_channel', CHANNEL_ID)

    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
            link_type, user_id, f_msg_id, channel_id, s_msg_id = await decode_link(base64_string)
        except ValueError as e:
            await message.reply_text(f"❌ Invalid link format: {str(e)}")
            return
        except Exception as e:
            await message.reply_text(f"❌ Error decoding link: {str(e)}")
            return

        if link_type == "HACKHEIST":
            if message.from_user.id != user_id:
                await message.reply_text("❌ You are not authorized to access this content!")
                return
            
            temp_msg = await message.reply("𝗥𝘂𝗸 𝗘𝗸 𝗦𝗲𝗰 👽..")
            try:
                messages = await get_messages(client, [f_msg_id], database_channel, bot_token)
                if not messages or all(msg is None for msg in messages):
                    await temp_msg.edit("Failed to fetch message. It may have been deleted or is inaccessible.")
                    return
            except Exception as e:
                await temp_msg.edit(f"Something went wrong: {str(e)}")
                print(f"Error getting message {f_msg_id} from {database_channel}: {e}")
                return
            finally:
                await temp_msg.delete()

            codeflix_msgs = []
            for msg in messages:
                if not msg:
                    continue
                filename = "Unknown"
                media_type = "Unknown"

                if msg.video:
                    media_type = "Video"
                    filename = msg.video.file_name if msg.video.file_name else "Unnamed Video"
                elif msg.document:
                    filename = msg.document.file_name if msg.document.file_name else "Unnamed Document"
                    media_type = "PDF" if filename.endswith(".pdf") else "Document"
                elif msg.photo:
                    media_type = "Image"
                    filename = "Image"
                elif msg.text:
                    media_type = "Text"
                    filename = "Text Content"

                caption = (
                    CUSTOM_CAPTION.format(
                        previouscaption=(msg.caption.html if msg.caption else "🔥 𝐇𝐈𝐃𝐃𝐄𝐍𝐒 🔥"),
                        filename=filename,
                        mediatype=media_type,
                    )
                    if bool(CUSTOM_CAPTION)
                    else (msg.caption.html if msg.caption else "")
                )

                reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

                try:
                    copied_msg = await msg.copy(
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=False,
                    )
                    if copied_msg:
                        codeflix_msgs.append(copied_msg)
                except Exception as e:
                    print(f"Failed to send individual message: {e}")
                    await message.reply_text("❌ Failed to send the content!")
                    return
            
            if codeflix_msgs:
                k = await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"<b>‼️ 𝐓𝐡𝐢𝐬 𝐋𝐄𝐂𝐓𝐔𝐑𝐄/𝐏𝐃𝐅 𝐰𝐢𝐥𝐥 𝐛𝐞 <u>𝗮𝘂𝘁𝗼-𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝗶𝗻 {humanize.naturaldelta(individual_delete_timer)}</u> 💀</b>\n\n"
                         f"<b>⚡ Watch Lecture now ✅ or Save it - Forward, Download & Keep in your Gallery before time runs out!</b>\n\n"
                         f"<b>🤝 Don’t forget—share with friends, knowledge grows when shared ❣️</b>\n\n"
                         f"<b>😎 Chill! Even after deletion, you can always re-access everything on our websites 😉</b>\n\n"
                         f"<b><a href='https://yashyasag.github.io/hiddens_officials'>✨ 𝗘𝘅𝗽𝗹𝗼𝗿𝗲 �_M𝗼𝗿𝗲 𝗪𝗲𝗯𝘀𝗶𝘁𝗲𝘀 ✨</a></b>",
                )
                codeflix_msgs.append(k)
                asyncio.create_task(delete_files(codeflix_msgs, client, message, delete_time=individual_delete_timer))
            return

        elif link_type == "batch" or link_type == "get":
            if s_msg_id is not None:
                if f_msg_id <= s_msg_id:
                    ids = list(range(f_msg_id, s_msg_id + 1))
                else:
                    ids = list(range(f_msg_id, s_msg_id - 1, -1))
            else:
                ids = [f_msg_id]

            temp_msg = await message.reply("�_R𝘂𝗸 𝗘𝗸 𝗦𝗲𝗰 👽..")
            try:
                messages = await get_messages(client, ids, database_channel, bot_token)
                print(f"Fetched {len(messages)} messages for channel_id={database_channel}, ids={ids}")
                if not messages or all(msg is None for msg in messages):
                    await temp_msg.edit("Failed to fetch messages. They may have been deleted or is inaccessible.")
                    return
            except Exception as e:
                await temp_msg.edit(f"Something went wrong: {str(e)}")
                print(f"Error getting messages from {database_channel}: {e}")
                return
            finally:
                await temp_msg.delete()

            codeflix_msgs = []
            user_id = message.from_user.id
            
            for msg in messages:
                if not msg:
                    continue
                filename = "Unknown"
                media_type = "Unknown"

                if msg.video:
                    media_type = "Video"
                    filename = msg.video.file_name if msg.video.file_name else "Unnamed Video"
                elif msg.document:
                    filename = msg.document.file_name if msg.document.file_name else "Unnamed Document"
                    media_type = "PDF" if filename.endswith(".pdf") else "Document"
                elif msg.photo:
                    media_type = "Image"
                    filename = "Image"
                elif msg.text:
                    media_type = "Text"
                    filename = "Text Content"

                caption = (
                    CUSTOM_CAPTION.format(
                        previouscaption=(msg.caption.html if msg.caption else "🔥 𝐇𝐈𝐃𝐃𝐄𝐍𝐒 🔥"),
                        filename=filename,
                        mediatype=media_type,
                    )
                    if bool(CUSTOM_CAPTION)
                    else (msg.caption.html if msg.caption else "")
                )

                base64_string2 = await encode_link(user_id=user_id, f_msg_id=msg.id, channel_id=database_channel)
                individual_button = InlineKeyboardButton("😁 𝗖𝗟𝗜𝗖𝗞 𝗧𝗢 𝗦𝗔𝗩𝗘 📥", url=f"https://t.me/{client.username}?start={base64_string2}")

                if DISABLE_CHANNEL_BUTTON:
                    reply_markup = None
                elif msg.reply_markup:
                    if msg.reply_markup.inline_keyboard:
                        new_keyboard = msg.reply_markup.inline_keyboard.copy()
                        new_keyboard.append([individual_button])
                        reply_markup = InlineKeyboardMarkup(new_keyboard)
                    else:
                        reply_markup = InlineKeyboardMarkup([individual_button])
                else:
                    reply_markup = InlineKeyboardMarkup([individual_button])

                try:
                    copied_msg = await msg.copy(
                        chat_id=message.from_user.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=protect_content,
                    )
                    if copied_msg:
                        codeflix_msgs.append(copied_msg)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    try:
                        copied_msg = await msg.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=protect_content,
                        )
                        if copied_msg:
                            codeflix_msgs.append(copied_msg)
                    except Exception as e:
                        print(f"Failed to send message after waiting: {e}")
                except Exception as e:
                    print(f"Failed to send message: {e}")

            if codeflix_msgs:
                k = await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"<b>🔥 Hurry! These Lectures/PDFs will be <u>deleted automatically in {humanize.naturaldelta(bulk_delete_timer)}</u> ⏳</b>\n\n"
                         f"<b>𝘚𝘰 𝘍𝘰𝘳 𝘚𝘢𝘷𝘪𝘯𝘨 𝘓𝘦𝘤𝘵𝘶𝘳𝘦/𝘗𝘥𝘧 𝘤𝘭𝘪𝘤𝘬 𝘰𝘯 𝘣𝘦𝘭𝘰𝘸 𝘣𝘶𝘵𝘵𝘰𝘯(😁 𝗖𝗟𝗜𝗖𝗞 𝗧𝗢 𝗦𝗔𝗩𝗘 📥) then 𝘠𝘰𝘶 𝘤𝘢𝘯 𝘚𝘢𝘷𝘦 𝘪𝘯 𝘎𝘢𝘭𝘭𝘦𝘳𝘺 😊</b>\n\n"
                         f"<b>😎 Don’t worry! Even after deletion, you can still re-access everything anytime through our websites 😘</b>\n\n"
                         f"<b> <a href=https://yashyasag.github.io/hiddens_officials>🌟 �_V𝗶𝘀𝗶𝘁 �_M𝗼𝗿𝗲 𝗪𝗲𝗯𝘀𝗶𝘁𝗲𝘀 🌟</a></b>",
                )
                codeflix_msgs.append(k)
                asyncio.create_task(delete_files(codeflix_msgs, client, message, delete_time=bulk_delete_timer))
            return

    reply_markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🔥 𝗠𝗔𝗜𝗡 𝗪𝗘𝗕𝗦𝗜𝗧𝗘 🔥", url="https://yashyasag.github.io/hiddens_officials")
        ],[
            InlineKeyboardButton("‼️ 𝗕𝗔𝗖𝗞𝗨𝗣 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 ‼️", url="https://t.me/+Sk3pfX_PWTQ3NmI1")
        ],[
            InlineKeyboardButton("👻 ᴄᴏɴᴛᴀᴄᴛ ᴜs 👻", url="https://t.me/TEAM_HIDDENS_BOT")
        ]]
    )
    await message.reply_text(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True
    )

@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    force_sub_channels = bot_settings.get('force_sub_channels', [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4])
    force_sub_names = bot_settings.get('force_sub_names', ["Channel 1", "Channel 2", "Channel 3", "Channel 4"])

    buttons = []
    for channel, name in zip(force_sub_channels, force_sub_names):
        if channel:
            try:
                chat = await client.get_chat(channel)
                buttons.append([InlineKeyboardButton(f"🌟 Join {name} 🌟", url=chat.invite_link)])
            except:
                buttons.append([InlineKeyboardButton(f"🌟 Join {name} 🌟", url="https://t.me/weebs_support")])
    
    try:
        buttons.append(
            [InlineKeyboardButton(
                text='♻️ 𝐓𝐑𝐘 𝐀𝐆𝐀𝐈𝐍 ♻️',
                url=f"https://t.me/{client.username}?start={message.command[1] if len(message.command) > 1 else ''}"
            )]
        )
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="Processing...")
    users = await full_userbase()
    await msg.edit(f"{len(users)} Users Are Using This Bot")

@Bot.on_message(filters.command('broadcast') & filters.private & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply("Reply to a message to broadcast it.")
        await asyncio.sleep(8)
        return await msg.delete()

    try:
        seconds = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        seconds = None

    query = await full_userbase()
    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0
    sent_messages = []

    pls_wait = await message.reply("<i>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ᴛɪʟʟ ᴡᴀɪᴛ ʙʀᴏᴏ...</i>")

    for chat_id in query:
        try:
            sent = await broadcast_msg.copy(chat_id)
            sent_messages.append((chat_id, sent.id))
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent = await broadcast_msg.copy(chat_id)
            sent_messages.append((chat_id, sent.id))
            successful += 1
        except UserIsBlocked:
            await del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            deleted += 1
        except:
            unsuccessful += 1
            pass
        total += 1

    status = f"""<b><u>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u>

ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ: <code>{total}</code>
ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ: <code>{successful}</code>
ʙʟᴏᴄᴋᴇᴅ ᴜꜱᴇʀꜱ: <code>{blocked}</code>
ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛꜱ: <code>{deleted}</code>
ᴜɴꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ: <code>{unsuccessful}</code></b>"""

    await pls_wait.edit(status)

    if seconds:
        await asyncio.sleep(seconds)
        for chat_id, msg_id in sent_messages:
            try:
                await client.delete_messages(chat_id, msg_id)
            except:
                pass

@Bot.on_message(filters.command('clone_bot') & filters.private & filters.user(ADMINS))
async def clone_bot_command(client: Client, message: Message):
    """Handle /clone_bot command to add a new bot token."""
    try:
        if len(message.command) < 2:
            await message.reply_text("Please provide a bot token.\nUsage: /clone_bot {bot_token}")
            return
        bot_token = message.command[1]

        if not bot_token.startswith("bot") and ":" not in bot_token:
            await message.reply_text("Invalid bot token format.")
            return

        try:
            test_client = Client("test_bot", api_id=APP_ID, api_hash=API_HASH, bot_token=bot_token)
            await test_client.start()
            bot_info = await test_client.get_me()
            await test_client.stop()
        except BadRequest:
            await message.reply_text("Invalid bot token. Please check and try again.")
            return
        except Exception as e:
            await message.reply_text(f"Error verifying bot token: {str(e)}")
            return

        if await get_bot(bot_token):
            await message.reply_text("This bot token is already added.")
            return

        await add_bot(
            token=bot_token,
            creator_id=message.from_user.id,
            force_sub_names=["Channel 1", "Channel 2", "Channel 3", "Channel 4"]
        )

        await message.reply_text(
            "✅ Bot added successfully!\n\n"
            "The bot is initialized with default settings and will start automatically with the main bot.\n"
            "Use the following commands in the cloned bot to configure it:\n"
            "/force_sub_channel - Set force-sub channels with custom button names\n"
            "/auto_delete - Set bulk auto-delete timer\n"
            "/individual_auto_delete - Set individual auto-delete timer\n"
            "/database_channel_id - Set database channel\n"
            "/protect_content - Toggle content protection"
        )

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Bot.on_message(filters.command('force_sub_channel') & filters.private)
async def force_sub_channel_command(client: Client, message: Message):
    """Handle /force_sub_channel command to set force-sub channels with custom button names."""
    bot_token = client.TG_BOT_TOKEN
    if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
        await message.reply_text("You are not authorized to manage this bot's settings.")
        return

    bot = await get_bot(bot_token) or {}
    force_sub_channels = bot.get('force_sub_channels', [None, None, None, None])
    force_sub_names = bot.get('force_sub_names', ["Channel 1", "Channel 2", "Channel 3", "Channel 4"])
    channel_list = "\n".join(f"{name}: {ch or 'Not set'}" for ch, name in zip(force_sub_channels, force_sub_names))

    await message.reply_text(
        f"Current Force Sub Channels:\n{channel_list}\n\n"
        "Send new channels in the format:\n"
        "BUTTON_NAME: CHANNEL_ID\n"
        "e.g., OPMASTER 01: -100939358352\n\n"
        "Send up to 4 lines (one per channel). Leave a line empty (e.g., 'OPMASTER 02:') to unset a channel. Reply with 'cancel' to abort.",
    )

    await set_session_data(
        message.from_user.id,
        {"action": "force_sub_channel", "bot_token": bot_token}
    )

@Bot.on_message(filters.command('auto_delete') & filters.private)
async def auto_delete_command(client: Client, message: Message):
    """Handle /auto_delete command to set bulk delete timer."""
    bot_token = client.TG_BOT_TOKEN
    if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
        await message.reply_text("You are not authorized to manage this bot's settings.")
        return

    bot = await get_bot(bot_token) or {}
    current_timer = humanize.naturaldelta(bot.get('bulk_delete_timer', FILE_AUTO_DELETE))

    await message.reply_text(
        f"Current Bulk Delete Timer: {current_timer}\n\n"
        "Send the new timer in seconds (e.g., 3600 for 1 hour). Reply with 'cancel' to abort."
    )

    await set_session_data(
        message.from_user.id,
        {"action": "auto_delete", "bot_token": bot_token}
    )

@Bot.on_message(filters.command('individual_auto_delete') & filters.private)
async def individual_auto_delete_command(client: Client, message: Message):
    """Handle /individual_auto_delete command to set individual delete timer."""
    bot_token = client.TG_BOT_TOKEN
    if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
        await message.reply_text("You are not authorized to manage this bot's settings.")
        return

    bot = await get_bot(bot_token) or {}
    current_timer = humanize.naturaldelta(bot.get('individual_delete_timer', INDIVIDUAL_AUTO_DELETE))

    await message.reply_text(
        f"Current Individual Delete Timer: {current_timer}\n\n"
        "Send the new timer in seconds (e.g., 259200 for 3 days). Reply with 'cancel' to abort."
    )

    await set_session_data(
        message.from_user.id,
        {"action": "individual_auto_delete", "bot_token": bot_token}
    )

@Bot.on_message(filters.command('database_channel_id') & filters.private)
async def database_channel_id_command(client: Client, message: Message):
    """Handle /database_channel_id command to set database channel."""
    bot_token = client.TG_BOT_TOKEN
    if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
        await message.reply_text("You are not authorized to manage this bot's settings.")
        return

    bot = await get_bot(bot_token) or {}
    current_channel = bot.get('database_channel', 'Not set')

    await message.reply_text(
        f"Current Database Channel: {current_channel}\n\n"
        "Send the new channel ID or username (e.g., @ChannelUsername or -100123456789). Reply with 'cancel' to abort."
    )

    await set_session_data(
        message.from_user.id,
        {"action": "database_channel_id", "bot_token": bot_token}
    )

@Bot.on_message(filters.command('protect_content') & filters.private)
async def protect_content_command(client: Client, message: Message):
    """Handle /protect_content command to toggle content protection."""
    bot_token = client.TG_BOT_TOKEN
    if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
        await message.reply_text("You are not authorized to manage this bot's settings.")
        return

    bot = await get_bot(bot_token) or {}
    current_value = bot.get('protect_content', PROTECT_CONTENT)
    new_value = not current_value

    await update_bot_settings(bot_token, {"protect_content": new_value})
    await message.reply_text(f"Protect Content has been turned {'On' if new_value else 'Off'}.")

@Bot.on_message(filters.private & filters.text & ~filters.command(['start', 'users', 'broadcast', 'clone_bot', 'force_sub_channel', 'auto_delete', 'individual_auto_delete', 'database_channel_id', 'protect_content']))
async def handle_settings_input(client: Client, message: Message):
    """Handle user input for settings commands."""
    try:
        session_data = await get_session_data(message.from_user.id)
        if not session_data or 'action' not in session_data or 'bot_token' not in session_data:
            return

        action = session_data['action']
        bot_token = session_data['bot_token']

        if not await is_bot_creator_or_admin(message.from_user.id, bot_token):
            await message.reply_text("You are not authorized to manage this bot's settings.")
            return

        if message.text.lower() == 'cancel':
            await clear_session_data(message.from_user.id)
            await message.reply_text("Action cancelled.")
            return

        if action == "force_sub_channel":
            lines = message.text.strip().split("\n")
            new_channels = [None] * 4
            new_names = ["Channel 1", "Channel 2", "Channel 3", "Channel 4"]
            for line in lines:
                try:
                    if ":" not in line:
                        continue
                    name, channel_id = [part.strip() for part in line.split(":", 1)]
                    if not name or not channel_id:
                        continue
                    index = min(len(new_channels) - 1, len([l for l in lines[:lines.index(line) + 1] if ":" in l]) - 1)
                    if channel_id.startswith("@"):
                        chat = await client.get_chat(channel_id)
                        new_channels[index] = str(chat.id)
                    else:
                        new_channels[index] = str(int(channel_id))
                    new_names[index] = name[:32]  # Limit button name to 32 characters
                except Exception as e:
                    await message.reply_text(f"Invalid format in line: {line}\nError: {str(e)}")
                    continue
            await update_bot_settings(bot_token, {
                "force_sub_channels": new_channels,
                "force_sub_names": new_names
            })
            channel_list = "\n".join(f"{name}: {ch or 'Not set'}" for ch, name in zip(new_channels, new_names))
            await message.reply_text(f"Force Sub Channels updated:\n{channel_list}")

        elif action == "auto_delete":
            try:
                timer = int(message.text.strip())
                if timer < 0:
                    raise ValueError("Timer cannot be negative.")
                await update_bot_settings(bot_token, {"bulk_delete_timer": timer})
                await message.reply_text(f"Bulk Delete Timer updated to {humanize.naturaldelta(timer)}.")
            except ValueError:
                await message.reply_text("Please send a valid number of seconds.")

        elif action == "individual_auto_delete":
            try:
                timer = int(message.text.strip())
                if timer < 0:
                    raise ValueError("Timer cannot be negative.")
                await update_bot_settings(bot_token, {"individual_delete_timer": timer})
                await message.reply_text(f"Individual Delete Timer updated to {humanize.naturaldelta(timer)}.")
            except ValueError:
                await message.reply_text("Please send a valid number of seconds.")

        elif action == "database_channel_id":
            channel_id = message.text.strip()
            try:
                if channel_id.startswith("@"):
                    chat = await client.get_chat(channel_id)
                    channel_id = str(chat.id)
                else:
                    channel_id = str(int(channel_id))
                await update_bot_settings(bot_token, {"database_channel": channel_id})
                await message.reply_text("Database Channel updated successfully.")
            except Exception as e:
                await message.reply_text(f"Invalid channel ID or username: {str(e)}")

        await clear_session_data(message.from_user.id)

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
