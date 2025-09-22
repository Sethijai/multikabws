# database.py
import pymongo
from config import DB_URI, DB_NAME, ADMINS, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, FILE_AUTO_DELETE, INDIVIDUAL_AUTO_DELETE, PROTECT_CONTENT, CHANNEL_ID

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]
user_data = database['users']
bot_data = database['bots']
session_data = database['sessions']  # New collection for session data

async def add_bot(token: str, creator_id: int, force_sub_channels: list = None, 
                 bulk_delete_timer: int = None, individual_delete_timer: int = None, 
                 protect_content: bool = True, database_channel: str = None):
    """Add a new bot to the database with default settings."""
    if force_sub_channels is None:
        force_sub_channels = [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]
    if bulk_delete_timer is None:
        bulk_delete_timer = FILE_AUTO_DELETE
    if individual_delete_timer is None:
        individual_delete_timer = INDIVIDUAL_AUTO_DELETE
    if database_channel is None:
        database_channel = CHANNEL_ID

    bot_data.insert_one({
        'token': token,
        'creator_id': creator_id,
        'force_sub_channels': force_sub_channels,
        'bulk_delete_timer': bulk_delete_timer,
        'individual_delete_timer': individual_delete_timer,
        'protect_content': protect_content,
        'database_channel': database_channel
    })

async def get_bot(token: str):
    """Retrieve bot details by token."""
    return bot_data.find_one({'token': token})

async def update_bot_settings(token: str, settings: dict):
    """Update settings for a specific bot."""
    bot_data.update_one({'token': token}, {'$set': settings})

async def is_bot_creator_or_admin(user_id: int, token: str):
    """Check if the user is the bot creator or an admin."""
    bot = await get_bot(token)
    if not bot:
        return False
    return user_id == bot['creator_id'] or user_id in ADMINS

async def present_user(user_id: int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})

async def full_userbase():
    user_docs = user_data.find()
    return [doc['_id'] for doc in user_docs]

async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})

async def set_session_data(user_id: int, data: dict):
    """Store session data for a user in MongoDB."""
    session_data.update_one(
        {'_id': user_id},
        {'$set': data},
        upsert=True
    )

async def get_session_data(user_id: int):
    """Retrieve session data for a user from MongoDB."""
    return session_data.find_one({'_id': user_id}) or {}

async def clear_session_data(user_id: int):
    """Clear session data for a user."""
    session_data.delete_one({'_id': user_id})
