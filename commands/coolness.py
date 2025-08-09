import discord

from discord.ext import commands
from discord import app_commands

from core.antispam import rate_limit_check
from database import Database
from util.embeds import ErrorEmbed, PaginatedTextTableEmbed
from util.guilds import guild_names_from_tags
from util.ranges import get_range_from_string, RangeTooLargeError



class Coolness(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="coolness",
        description="Shows your playtime in hours"
    )
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Number of days ago, or a range like '0,7' (defaults to 7 days)",
        order="The order to sort in (descending by default)",
    )
    @app_commands.choices(order=[
        app_commands.Choice(name="Ascending", value="ASC"),
        app_commands.Choice(name="Descending", value="DESC"),
    ])
    @rate_limit_check()  # Anti-spam check to limit how often this command can be run
    async def coolness(
        self,
        interaction: discord.Interaction,
        guilds: str,
        range: str = "7",
        order: app_commands.Choice[str] = "DESC"
    ):
        """
        Shows the "coolness" leaderboard (playtime hours) for specified guilds and date range.

        Workflow:
        1. Parse and validate the date range (default 7 days).
        2. Resolve guild tags into guild names.
        3. Query DB for playtime counts grouped by player and guild.
        4. Display results in a paginated embed sorted by coolness.
        """
        await interaction.response.defer()

        # Parse the provided guild tags (if any) and resolve them to full guild names
        if guilds:
            tags = [tag.strip() for tag in guilds.split(",") if tag.strip()]
            guild_names, _ = await guild_names_from_tags(tags)

        # If no valid guilds were found, abort
        if not guild_names:
            return await interaction.followup.send(
                embed=ErrorEmbed("Guilds not found."),
                ephemeral=True
            )

        # Parse the provided range
        try:
            range = await get_range_from_string(range)
        except RangeTooLargeError:
            return await interaction.followup.send(
                embed=ErrorEmbed("Range exceeds maximum range of 50 days.")
            )

        # If range parsing failed, abort
        if not range:
            return await interaction.response.send_message(
                embed=ErrorEmbed("Invalid range input"),
                ephemeral=True
            )
        
        start_ts, end_ts = range

        # Create placeholders for the SQL query (based on how many guilds were provided)
        placeholders = "(" + ",".join(["%s"] * len(guild_names)) + ")"

        # SQL query to get each player's "coolness" (hours online) for the given guilds and date range
        query = f'''
SELECT A.guild, B.name, A.coolness
FROM
  (SELECT guild, uuid, COUNT(*) as coolness 
  FROM 
    activity_members
    WHERE guild IN {placeholders}
    AND timestamp >= %s AND timestamp <= %s
    GROUP BY uuid, guild) A
  JOIN uuid_name B ON A.uuid=B.uuid  
ORDER BY A.coolness {order};
'''

        # Combine guild names with the start and end timestamps for query parameters
        values = list(guild_names) + [str(start_ts), str(end_ts)]

        # Execute the query and retrieve rows
        rows = await Database.fetch(query, values)

        # If no results were found, inform the user
        if not rows:
            return await interaction.followup.send(
                embed=ErrorEmbed("No results found."),
                ephemeral=True
            )

        # Prepare the table data for the embed (guild | username | hours online)
        table_rows = [
            (entry["guild"], entry["name"], f"{entry['coolness']:,}")
            for entry in rows
        ]

        # Send the paginated table as an embed
        await PaginatedTextTableEmbed.send(
            interaction,
            ["Guild", "Username", "Hours Online"],
            table_rows,
            title=(
                f"Coolness Leaderboard for "
                f"{', '.join(guild_names) if len(guild_names) > 1 else guild_names[0]}"
            ),
            rows_per_page=25
        )



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Coolness(bot))
