import discord

from discord import app_commands
from discord.ext import commands

from core.antispam import rate_limit_check
from database import Database
from util.embeds import ErrorEmbed, PaginatedTextTableEmbed
from util.guilds import guild_names_from_tags
from util.ranges import RangeTooLargeError, get_range_from_string


class AvgCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="average",
        description="Averages of guild members online over a time range."
    )
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Number of days ago, or a range like '0,7'",
    )
    @rate_limit_check()
    async def average(
        self,
        interaction: discord.Interaction,
        guilds: str = None,
        range: str = "7"
    ):
        """
        Shows the average number of guild members online during a specified date range.

        Workflow:
        1. Parse and validate the date range (default: last 7 days).
        2. Optionally filter by guild tags.
        3. Query database for average player counts.
        4. Display results in a paginated table.
        """
        await interaction.response.defer()

        # Parse range input from string input into left and right unix timestamps
        try:
            range_values = await get_range_from_string(range)
        except RangeTooLargeError:
            return await interaction.followup.send(
                embed=ErrorEmbed("Range exceeds maximum range of 50 days.")
            )

        if not range_values:
            return await interaction.followup.send(
                embed=ErrorEmbed("Invalid range input")
            )
        
        left_days, right_days = range_values

        # Build base query — selects guilds and averages member counts
        query = (
            "SELECT guild, ROUND(AVG(count), 1) AS avg_count "
            "FROM guild_member_count "
            "WHERE time >= %s AND time <= %s"
        )
        params = [int(left_days), int(right_days)]
        unidentified = []

        # If guild tags are provided, resolve them to full names
        if guilds:
            tags = guilds.split(",")
            names, unidentified = await guild_names_from_tags(tags)

            # If no valid guild names found, send error
            if not names:
                return await interaction.followup.send(
                    embed=ErrorEmbed(f"Unknown guilds: {' '.join(unidentified)}")
                )

            # Add guild filtering to the query
            query += f" AND guild IN ({','.join(['%s'] * len(names))})"
            params.extend(names)

        # Sort by highest average and limit to 50 results
        query += " GROUP BY guild ORDER BY avg_count DESC LIMIT 50"

        # Fetch results from the database
        rows = await Database.fetch(query, params)

        if not rows:
            return await interaction.followup.send(
                embed=ErrorEmbed("No data available in the given range.")
            )

        # Format the table for display
        table = [[row["guild"], f"{row['avg_count']:.1f}"] for row in rows]

        # Send as a paginated text table
        await PaginatedTextTableEmbed.send(
            interaction,
            ["Guild", "Avg Players Online"],
            table,
            title=f"Average Member Count ({range or '7 days'})",
            rows_per_page=25
        )



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(AvgCog(bot))
