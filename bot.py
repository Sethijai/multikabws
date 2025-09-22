# bot.py
import asyncio
import os
from pyrogram import Client, idle
from aiohttp import web
from plugins.route import web_server
from config import *
from database.database import dbclient, get_bot

async def start_bot_with_token(bot_token, api_id, api_hash, workers):
    """Start a bot with the given token."""
    try:
        app = Client(
            f"bot_{bot_token[:10]}",  # Unique session name
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            workers=workers,
            plugins={"root": "plugins"}
        )
        app.TG_BOT_TOKEN = bot_token  # Attach token to client
        await app.start()
        bot_info = await app.get_me()
        print(f"Bot @{bot_info.username} started successfully.")
        return app
    except Exception as e:
        print(f"Failed to start bot with token ending {bot_token[-6:]}: {e}")
        return None

async def main():
    api_id = int(os.environ.get("APP_ID"))
    api_hash = os.environ.get("API_HASH")
    main_bot_token = os.environ.get("TG_BOT_TOKEN")
    workers = int(os.environ.get("TG_BOT_WORKERS", 4))

    # Start main bot
    main_bot = await start_bot_with_token(main_bot_token, api_id, api_hash, workers)
    if not main_bot:
        print("Main bot failed to start. Exiting.")
        return

    # Start cloned bots from database
    bot_collection = dbclient[os.environ.get("DB_NAME")]['bots']
    cloned_bots = []
    async for bot_doc in bot_collection.find():
        bot_token = bot_doc.get('token')
        if bot_token and bot_token != main_bot_token:  # Avoid restarting main bot
            bot_client = await start_bot_with_token(bot_token, api_id, api_hash, workers)
            if bot_client:
                cloned_bots.append(bot_client)

    # Start web server
    port = int(os.environ.get("PORT", 8080))
    web_app = await web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server running on port {port}")

    # Keep all bots running
    await idle()

    # Cleanup
    await main_bot.stop()
    for bot in cloned_bots:
        await bot.stop()
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
