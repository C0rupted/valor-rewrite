import discord, logging
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from database.connection import Database
from util.embeds import PaginatedTextTableEmbed, ErrorEmbed
from util.guilds import guild_name_from_tag
from util.requests import request


class Activity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="activity", description="Show last join times for all players in a guild")
    @app_commands.describe(guild="The guild tag (e.g. ANO)", order="The order to sort in (descending by default)",)
    @app_commands.choices(order=[
        app_commands.Choice(name="Ascending", value="asc"),
        app_commands.Choice(name="Descending", value="desc")
    ])
    async def activity(self, interaction: discord.Interaction, guild: str, order: app_commands.Choice[str] = "desc"):
        await interaction.response.defer()

        guild_name = await guild_name_from_tag(guild)

        if not guild_name:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid guild tag."))

        res = await request(f"https://api.wynncraft.com/v3/guild/{guild_name}")
        
        if not res:
            return await interaction.followup.send(embed=ErrorEmbed("Failed to fetch guild data."))
        members_data = res["members"]

        member_set = set()
        for rank in members_data:
            if isinstance(members_data[rank], dict):
                member_set.update(members_data[rank])

        members_list = list(member_set)
        if not members_list:
            return await interaction.followup.send(embed=ErrorEmbed("Guild has no members."))

        placeholders = ','.join(['%s'] * len(members_list))
        query = f"SELECT name, lastjoin FROM player_last_join WHERE name IN ({placeholders})"
        res = await Database.fetch(query, members_list)
        last_join_times = {result["name"]: result["lastjoin"] for result in res}

        now = datetime.utcnow()
        rows = []
        for name in members_list:
            try:
                stamp = last_join_times[name]
            except KeyError:
                continue

            if stamp:
                delta = now - datetime.utcfromtimestamp(stamp)
                display = f"{delta.days}d {delta.seconds // 3600}h"
            else:
                display = "30d+"
            rows.append((name, display))

        # Sort by longest inactive first
        rows.sort(key=lambda r: (r[1] != "30d+", int(r[1].rstrip("dh").split("d")[0]) if r[1] != "30d+" else 9999), reverse=(True if order == "desc" else False))

        await PaginatedTextTableEmbed.send(interaction, [" Name ", " Last Join "], rows, title=f"Member Activity of {guild_name}: ({len(rows)})", rows_per_page=20)

async def setup(bot: commands.Bot):
    await bot.add_cog(Activity(bot))
