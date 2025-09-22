# bot.py
import asyncio
import os
from pyrogram import Client, idle
from aiohttp import web
from plugins.route import web_server
from config import *
from database.database import dbclient, get_bot

class Bot:
    def __init__(self):
        self.api_id = int(os.environ.get("APP_ID"))
        self.api_hash = os.environ.get("API_HASH")
        self.main_bot_token = os.environ.get("TG_BOT_TOKEN")
        self.workers = int(os.environ.get("TG_BOT_WORKERS", 4))
        self.clients = []

    async def start_bot_with_token(self, bot_token):
        """Start a bot with the given token."""
        try:
            app = Client(
                f"bot_{bot_token[:10]}",  # Unique session name
                api_id=self.api_id,
                api_hash=self.api_hash,
                bot_token=bot_token,
                workers=self.workers,
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

    async def start(self):
        """Start the main bot and all cloned bots."""
        # Start main bot
        main_bot = await self.start_bot_with_token(self.main_bot_token)
        if not main_bot:
            print("Main bot failed to start. Exiting.")
            return
        self.clients.append(main_bot)

        # Start cloned bots from database
        bot_collection = dbclient[os.environ.get("DB_NAME")]['bots']
        async for bot_doc in bot_collection.find():
            bot_token = bot_doc.get('token')
            if bot_token and bot_token != self.main_bot_token:  # Avoid restarting main bot
                bot_client = await self.start_bot_with_token(bot_token)
                if bot_client:
                    self.clients.append(bot_client)

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

    async def stop(self):
        """Stop all bots and cleanup web server."""
        for client in self.clients:
            await client.stop()
        self.clients.clear()

    def run(self):
        """Run the bot asynchronously."""
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.start())
        finally:
            loop.run_until_complete(self.stop())
            loop.close()
