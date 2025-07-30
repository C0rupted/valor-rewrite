from typing import Union
import discord

from discord import app_commands
from discord.ext import commands

from util.embeds import ErrorEmbed, TextTableEmbed
from util.guilds import guild_name_from_tag
from util.mappings import RANK_SYMBOL_MAP
from util.requests import request


class OnlineCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: Union[app_commands.Command, app_commands.ContextMenu]):
        """
        This function will be called after any command successfully completes.
        """
        print(f"Command '{ctx.command.name}' completed in {ctx.guild.name} by {ctx.author.name}")
        # Add your desired code here
        await ctx.send(f"Command '{ctx.command.name}' finished!")





async def setup(bot):
    await bot.add_cog(OnlineCommand(bot))
