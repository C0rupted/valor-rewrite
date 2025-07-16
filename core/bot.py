# core/bot.py

import discord, logging
from discord.ext import commands

from core.config import config
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
        await Database.init_pool()

    async def load_extensions(self):
        extensions = [
            "core.errors",
            "cogs.profile",
            "cogs.uniform"
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

        for guild_id in config.ANO_COMMANDS_GUILD_IDS:
            guild = discord.Object(id=int(guild_id))
            try:
                await self.tree.sync(guild=guild)
                logging.info(f"✅ Synced commands to guild {guild.id}")
            except discord.Forbidden:
                logging.warning(f"⚠️ Missing access to sync commands in guild {guild.id}")
        logging.info("🌐 Synced slash commands")
        logging.info("✅ Bot is ready")

    async def close(self):
        await Database.close_pool()
        await super().close()


def run_bot():
    setup_logging()
    bot = ValorBot()
    bot.run(config.TOKEN)
