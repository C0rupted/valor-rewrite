# core/bot.py

import discord, logging
from discord.ext import commands

from core.config import settings
from core.logging import setup_logging
from database.connection import Database


class ValorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="",  # Slash-only, no text prefix at all
            intents=intents,
            help_command=None,
            log_handler=None
        )

    async def setup_hook(self):
        await self.load_extensions()
        await self.tree.sync()
        logging.info("🌐 Synced slash commands")
        await Database.init_pool()

    async def load_extensions(self):
        extensions = [
            "core.errors",
            # Add slash command cogs here:
            # "cogs.guild",
            # "cogs.profile",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logging.info(f"✅ Loaded extension: {ext}")
            except Exception as e:
                logging.error(f"❌ Failed to load extension {ext}: {e}")

    async def on_ready(self):
        logging.info(f"✅ Logged in as {self.user} (ID: {self.user.id})")

    async def close(self):
        await Database.close_pool()
        await super().close()


def run_bot():
    setup_logging()
    bot = ValorBot()
    bot.run(settings.TOKEN)
