# helper_func.py
import base64
import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS, PROTECT_CONTENT, FILE_AUTO_DELETE, INDIVIDUAL_AUTO_DELETE, CHANNEL_ID
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, ChannelInvalid, ChatAdminRequired
from pyrogram.errors import FloodWait
from typing import Tuple, Union
from database.database import get_bot

async def is_subscribed(filter, client, update):
    """Check if a user is subscribed to all required channels for the bot."""
    user_id = update.from_user.id
    if user_id in ADMINS:
        return True

    bot_token = client.TG_BOT_TOKEN
    bot_settings = await get_bot(bot_token) or {}
    force_sub_channels = bot_settings.get('force_sub_channels', [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4])

    for channel in force_sub_channels:
        if not channel:
            continue
        try:
            member = await client.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            print(f"Error checking subscription for channel {channel}: {e}")
            return False
    return True

subscribed = filters.create(is_subscribed)

async def encode(string: str) -> str:
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    return base64_bytes.decode("ascii")

async def decode(base64_string: str) -> str:
    try:
        base64_bytes = base64_string.encode("ascii")
        string_bytes = base64.b64decode(base64_bytes)
        return string_bytes.decode("ascii")
    except Exception as e:
        print(f"Decoding error: {e}")
        raise ValueError("Invalid encoded string")

async def encode_link(user_id: int = None, f_msg_id: int = None, channel_id: Union[int, str] = None, s_msg_id: int = None) -> str:
    if user_id:
        string = f"HACKHEIST-{user_id}-{f_msg_id}-{channel_id}"
    elif s_msg_id:
        string = f"batch-{f_msg_id}-{channel_id}-{s_msg_id}"
    else:
        string = f"get-{f_msg_id * abs(int(channel_id))}"
    return f"https://t.me/{Bot.username}?start={await encode(string)}"

async def decode_link(base64_string: str) -> Tuple[str, int, int, Union[int, str], int]:
    decoded = await decode(base64_string)
    parts = decoded.split("-", maxsplit=3)
    if len(parts) < 3:
        raise ValueError("Invalid link format")
    
    link_type = parts[0]
    if link_type == "HACKHEIST":
        user_id = int(parts[1])
        f_msg_id = int(parts[2])
        channel_id = parts[3]
        s_msg_id = None
    elif link_type == "batch":
        f_msg_id = int(parts[1])
        channel_id = parts[2]
        s_msg_id = int(parts[3])
        user_id = None
    else:
        raise ValueError("Unknown link type")
    
    return link_type, user_id, f_msg_id, channel_id, s_msg_id

async def get_message_id(client, message):
    if message.forward_from_chat:
        return message.forward_from_chat.id, message.forward_from_message_id
    elif message.text and (message.text.startswith("https://t.me/") or message.text.startswith("t.me/")):
        if message.text.startswith("https://"):
            link = message.text
        else:
            link = "https://" + message.text
        try:
            pattern = r"https://t\.me/(?:c/)?(?:@)?([a-zA-Z0-9_]+)/(\d+)"
            match = re.match(pattern, link)
            if not match:
                return None, None
            channel_username, message_id = match.groups()
            if channel_username.startswith("-"):
                channel_id = int(channel_username)
            else:
                chat = await client.get_chat(f"@{channel_username}" if not channel_username.startswith("@") else channel_username)
                channel_id = chat.id
            return channel_id, int(message_id)
        except Exception as e:
            print(f"Error parsing link: {e}")
            return None, None
    return None, None

async def get_messages(client, message_ids, channel_id, bot_token: str = None):
    """Fetch messages from a specified channel, using bot-specific database channel if available."""
    if bot_token:
        bot = await get_bot(bot_token)
        if bot and bot.get('database_channel'):
            channel_id = bot['database_channel']

    messages = []
    total_messages = 0

    if not message_ids:
        print("No message IDs provided")
        return messages
    if not channel_id:
        print("No channel ID provided")
        return messages

    try:
        await client.get_chat(channel_id)
        print(f"Access confirmed for channel {channel_id}")
    except ChannelInvalid:
        print(f"Invalid channel ID: {channel_id}")
        return messages
    except ChatAdminRequired:
        print(f"Bot requires admin access to channel: {channel_id}")
        return messages
    except Exception as e:
        print(f"Error accessing channel {channel_id}: {e}")
        return messages

    while total_messages < len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=channel_id,
                message_ids=temb_ids
            )
            valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
            if valid_msgs:
                print(f"Fetched {len(valid_msgs)} messages for IDs {temb_ids} in channel {channel_id}")
            else:
                print(f"No valid messages found for IDs {temb_ids} in channel {channel_id}")
            messages.extend(valid_msgs)
        except FloodWait as e:
            print(f"FloodWait: Waiting {e.value} seconds for channel {channel_id}")
            await asyncio.sleep(e.value)
            try:
                msgs = await client.get_messages(
                    chat_id=channel_id,
                    message_ids=temb_ids
                )
                valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
                if valid_msgs:
                    print(f"Fetched {len(valid_msgs)} messages for IDs {temb_ids} in channel {channel_id} after FloodWait")
                else:
                    print(f"No valid messages found for IDs {temb_ids} in channel {channel_id} after FloodWait")
                messages.extend(valid_msgs)
            except Exception as e:
                print(f"Error after FloodWait for IDs {temb_ids} in channel {channel_id}: {e}")
        except Exception as e:
            print(f"Error fetching messages for IDs {temb_ids} in channel {channel_id}: {e}")
        total_messages += len(temb_ids)

    if messages:
        print(f"Successfully fetched {len(messages)} messages from channel {channel_id}")
    else:
        print(f"No messages fetched for IDs {message_ids} in channel {channel_id}")
    return messages

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

subscribed = filters.create(is_subscribed)
       
