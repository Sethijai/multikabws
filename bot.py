# bot.py
import os
import asyncio
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from config import *
from database.database import dbclient, get_bot
from plugins.start import (
    start_command, not_joined, get_users, send_text,
    clone_bot_command, force_sub_channel_command, auto_delete_command,
    individual_auto_delete_command, database_channel_id_command, protect_content_command,
    handle_settings_input
)
from plugins.link_generator import genlink_command, batch_command, nbatch_command, custom_batch_command, handle_custom_batch_input
from plugins.channel_post import forward_to_channel
from plugins.route import web_server  # Changed from plugins.web_server to route

async def initialize_bot(bot_token, bot_name):
    """Initialize a bot with the given token and name."""
    try:
        bot = Client(
            name=bot_name,
            api_id=APP_ID,
            api_hash=API_HASH,
            bot_token=bot_token,
            workers=TG_BOT_WORKERS,
            plugins={"root": "plugins"}
        )
        bot.TG_BOT_TOKEN = bot_token  # Attach token to client for use in handlers

        # Register handlers
        bot.add_handler(MessageHandler(start_command, filters.command('start') & filters.private & subscribed))
        bot.add_handler(MessageHandler(not_joined, filters.command('start') & filters.private))
        bot.add_handler(MessageHandler(get_users, filters.command('users') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(send_text, filters.command('broadcast') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(clone_bot_command, filters.command('clone_bot') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(force_sub_channel_command, filters.command('force_sub_channel') & filters.private))
        bot.add_handler(MessageHandler(auto_delete_command, filters.command('auto_delete') & filters.private))
        bot.add_handler(MessageHandler(individual_auto_delete_command, filters.command('individual_auto_delete') & filters.private))
        bot.add_handler(MessageHandler(database_channel_id_command, filters.command('database_channel_id') & filters.private))
        bot.add_handler(MessageHandler(protect_content_command, filters.command('protect_content') & filters.private))
        bot.add_handler(MessageHandler(handle_settings_input, filters.private & filters.text))
        bot.add_handler(MessageHandler(genlink_command, filters.command('genlink') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(batch_command, filters.command('batch') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(nbatch_command, filters.command('nbatch') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(custom_batch_command, filters.command('custom_batch') & filters.private & filters.user(ADMINS)))
        bot.add_handler(MessageHandler(handle_custom_batch_input, filters.private & filters.text))
        bot.add_handler(MessageHandler(forward_to_channel, filters.channel & filters.user(ADMINS)))

        await bot.start()
        bot_info = await bot.get_me()
        print(f"Bot @{bot_info.username} started with token {bot_token[-6:]}")
        return bot
    except Exception as e:
        print(f"Failed to start bot with token {bot_token[-6:]}: {e}")
        return None

async def main():
    """Initialize and run all bots from the database."""
    main_bot = await initialize_bot(TG_BOT_TOKEN, "main_bot")
    if not main_bot:
        print("Failed to start main bot. Exiting.")
        return

    # Query all bot tokens from the database
    bot_collection = dbclient[DB_NAME]['bots']
    bots = bot_collection.find()
    bot_clients = [main_bot]

    # Initialize cloned bots
    async for bot_data in bots:
        bot_token = bot_data.get('token')
        if bot_token and bot_token != TG_BOT_TOKEN:  # Skip main bot token
            bot_name = f"cloned_bot_{bot_token[-6:]}"
            cloned_bot = await initialize_bot(bot_token, bot_name)
            if cloned_bot:
                bot_clients.append(cloned_bot)

    print(f"Running {len(bot_clients)} bots (1 main + {len(bot_clients)-1} cloned)")
    
    # Start web server
    if 'PORT' in os.environ:
        web_app = await web_server()
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', int(os.environ['PORT']))
        await site.start()

    # Keep bots running
    await asyncio.Event().wait()

if __name__ == "__main__":
    print(f"Starting bot with Pyrogram v{__version__} (Layer {layer})")
    asyncio.run(main())
