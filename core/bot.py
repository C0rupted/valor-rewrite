import discord, logging, traceback
from discord.ext import commands

from core.config import config
from core.logging import setup_logging
from database.connection import Database
from util.embeds import ErrorEmbed


class ValorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="",  # Slash-only, no text prefix at all
            intents=intents,
            help_command=None,
            log_handler=None
        )

        self.tree.error(coro=self.on_app_command_error)

    async def setup_hook(self):
        await self.load_extensions()
        await self.tree.sync()
        await Database.init_pool()

    async def load_extensions(self):
        extensions = [
            "core.errors",
            "cogs.profile",
            "cogs.uniform",
            "cogs.pools",
            "cogs.annihilation_tracker",
            "cogs.uptime",
            "cogs.sus",
            "cogs.settings",
            "cogs.leaderboard",
            "cogs.graids",
            "cogs.average",
            "cogs.ffa",
            "cogs.pings",
            "cogs.coolness",
            "cogs.online",
            "cogs.activity",
            "cogs.blacklist",
            "cogs.completion",
            "cogs.history"
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                logging.info(f"Loaded extension: {ext}")
            except Exception as e:
                logging.error(f"Failed to load extension {ext}: {e}")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

        for guild_id in config.ANO_COMMANDS_GUILD_IDS:
            guild = discord.Object(id=int(guild_id))
            try:
                await self.tree.sync(guild=guild)
                logging.info(f"Synced commands to guild {guild.id}")
            except discord.Forbidden:
                logging.warning(f"Missing access to sync commands in guild {guild.id}")

        logging.info("Successfully synced all slash commands")
        logging.info("Bot is ready")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        # Log full traceback
        logging.error(f"An error occurred while executing a {error.command} command:")
        logging.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))

        # Send error message to user
        embed = ErrorEmbed("An unexpected error occurred while executing the command.", footer="Please contact ANO and report this bug")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)



    async def close(self):
        await Database.close_pool()
        await super().close()


def run_bot():
    setup_logging()

    bot = ValorBot()
    if config.TESTING:
        bot.run(config.TOKEN)
    else:
        bot.run(config.TOKEN, log_handler=None)
