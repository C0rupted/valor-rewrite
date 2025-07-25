import discord, time

from discord import app_commands
from discord.ext import commands

from database.connection import Database
from util.embeds import TextTableEmbed, ErrorEmbed
from util.guilds import guild_names_from_tags
from util.ranges import get_range_from_string


class AvgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="average", description="Averages of guild members online over a time range.")
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Number of days ago, or a range like '0,7'",
    )
    async def average(self, interaction: discord.Interaction, guilds: str = None, range: str = None):
        await interaction.response.defer()

        now = time.time()

        # Parse range
        try:
            left_days, right_days = await get_range_from_string(range or "7")
        except ValueError as e:
            return await interaction.followup.send(embed=ErrorEmbed(str(e)))

        # Parse guild tags
        query = "SELECT guild, ROUND(AVG(count), 1) AS avg_count FROM guild_member_count WHERE time >= %s AND time <= %s"
        params = [int(left_days), int(right_days)]
        unidentified = []

        if guilds:
            tags = guilds.split()
            names, unidentified = await guild_names_from_tags(tags)
            if not names:
                return await interaction.followup.send(embed=ErrorEmbed(f"Unknown guilds: {' '.join(unidentified)}"))

            query += f" AND guild IN ({','.join(['%s'] * len(names))})"
            params.extend(names)

        query += " GROUP BY guild ORDER BY avg_count DESC LIMIT 50"

        rows = await Database.fetch(query, params)

        if not rows:
            return await interaction.followup.send(embed=ErrorEmbed("No data available in the given range."))

        # Format output
        table = [[row["guild"], f"{row['avg_count']:.1f}"] for row in rows]
        title = f"Average Member Count ({range or '7 days'})"
        if unidentified:
            title += f"\nUnidentified: {' '.join(unidentified)}"

        embed = TextTableEmbed([" Guild ", " Avg Online "], table, title=title)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AvgCog(bot))
