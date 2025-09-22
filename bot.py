# bot.py
import asyncio
import os
from pyrogram import Client, idle
from aiohttp import web
from plugins.route import web_server
from database.database import dbclient
from config import API_HASH, APP_ID, TG_BOT_TOKEN, TG_BOT_WORKERS, DB_NAME

class Bot:
    def __init__(self):
        if APP_ID is None:
            raise ValueError("APP_ID environment variable is not set.")
        self.api_id = int(APP_ID)  # Convert APP_ID to int, raise error if invalid
        self.api_hash = API_HASH or ""
        self.main_bot_token = TG_BOT_TOKEN or ""
        self.workers = TG_BOT_WORKERS or 4
        self.db_name = DB_NAME
        self.clients = []

        if not all([self.api_id, self.api_hash, self.main_bot_token, self.db_name]):
            raise ValueError("Missing required configuration: APP_ID, API_HASH, TG_BOT_TOKEN, or DB_NAME.")

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
        try:
            bot_collection = dbclient[self.db_name]['bots']
            async for bot_doc in bot_collection.find():
                bot_token = bot_doc.get('token')
                if bot_token and bot_token != self.main_bot_token:  # Avoid restarting main bot
                    bot_client = await self.start_bot_with_token(bot_token)
                    if bot_client:
                        self.clients.append(bot_client)
        except Exception as e:
            print(f"Failed to access 'bots' collection in database '{self.db_name}': {e}")

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
