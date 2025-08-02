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

    @app_commands.command(name="online", description="Shows who's online in a guild")
    @app_commands.describe(guild="The guild tag to lookup")
    async def online(self, interaction: discord.Interaction, guild: str):
        await interaction.response.defer()

        name = await guild_name_from_tag(guild)
        res = await request(f"https://api.wynncraft.com/v3/guild/{name}")

        if "members" not in res:
            return await interaction.followup.send(embed=ErrorEmbed(f"Guild does not exist."))

        online_members = [
            (name, RANK_SYMBOL_MAP.get(rank, rank), member["server"])
            for rank, v in res["members"].items()
            if rank != "total"
            for name, member in v.items()
            if member["online"]
        ]

        if not online_members:
            return await interaction.followup.send(embed=ErrorEmbed("There are no members online."))

        embed = TextTableEmbed(
            [" Name ", " Rank ", " World "],
            sorted(online_members, key=lambda x: len(x[1]), reverse=True),
            title=f"Members of {name} online ({len(online_members)})",
            color=0x7785cc,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OnlineCommand(bot))
