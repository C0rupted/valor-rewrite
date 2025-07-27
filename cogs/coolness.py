import discord, time, logging

from discord.ext import commands
from discord import app_commands

from database.connection import Database
from util.embeds import ErrorEmbed, TextTableEmbed
from util.guilds import guild_names_from_tags
from util.ranges import get_range_from_string

# CURRENTLY BROKEN (sql query being weird, idk why)

class CoolnessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coolness", description="The leaderboard (but for coolness)")
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Number of days ago, or a range like '0,7'",
        order="The order to sort in (descending by default)",
    )
    @app_commands.choices(order=[
        app_commands.Choice(name="Ascending", value="ASC"),
        app_commands.Choice(name="Descending", value="DESC"),
    ])
    async def coolness(self, interaction: discord.Interaction, guilds: str = None, range: str = "7", order: app_commands.Choice[str] = "DESC"):
        await interaction.response.defer()

        if guilds:
            tags = [tag.strip() for tag in guilds.split(",") if tag.strip()]
            guild_names, _ = await guild_names_from_tags(tags)
        else:
            guild_names = ["ANO"]

        if not guild_names:
            return await interaction.followup.send(embed=ErrorEmbed("Guilds not found."), ephemeral=True)

        range = await get_range_from_string(range)

        if not range:
            return await interaction.response.send_message(embed=ErrorEmbed("Invalid range input"), ephemeral=True)
        
        start_ts, end_ts = range
        logging.info(start_ts)
        logging.info(end_ts)


        placeholders = "(" + ",".join(["%s"] * len(guild_names)) + ")"

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

        values = list(guild_names) + [str(start_ts), str(end_ts)]

        logging.info(query)
        logging.info(values)
        rows = await Database.fetch(query, values)

        if not rows:
            logging.info(rows)
            return await interaction.followup.send(embed=ErrorEmbed("No results found."), ephemeral=True)

        table_rows = [(guild, name, f"{coolness:,}") for guild, name, coolness in rows]
        table = TextTableEmbed(
            title="Coolness Leaderboard",
            headers=[" Guild ", " Username ", " Hours Online "],
            rows=table_rows
        )

        await interaction.followup.send(embed=table)

async def setup(bot):
    await bot.add_cog(CoolnessCog(bot))
