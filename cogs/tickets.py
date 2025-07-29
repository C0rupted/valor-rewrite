import discord, math, time, logging
from discord import app_commands
from discord.ext import commands

from core.config import config
from database.connection import Database
from util.embeds import ErrorEmbed, PaginatedTextTableEmbed
from util.uuid import get_uuid_from_name
from util.ranges import get_range_from_string



def do_ticket_math(value: float, base: float) -> int:
    return math.floor(math.log((math.floor(float(value) + 0.5) / base) + 1, 1.05) + 0.5)


async def get_tickets(start_timestamp: float = None):
    range_condition = f"AND PDR.time >= {start_timestamp}" if start_timestamp else ""

    query = f"""
SELECT 
    GMC.name,
    SUM(CASE WHEN PDR.label = 'g_wars' THEN PDR.delta ELSE 0 END) AS wars_gain,
    SUM(CASE WHEN PDR.label = 'gu_gxp' THEN PDR.delta ELSE 0 END) AS gxp_gain,
    SUM(CASE WHEN PDR.label IN ('g_The Canyon Colossus', "g_Orphion's Nexus of Light", 'g_Nest of the Grootslangs', "g_The Nameless Anomaly") THEN PDR.delta ELSE 0 END) AS raids_gain,
    COALESCE(MAX(TB.ticket_bonus), 0) AS ticket_bonus
FROM 
    guild_member_cache GMC
JOIN 
    uuid_name UN ON GMC.name = UN.name
JOIN 
    player_delta_record PDR ON UN.uuid = PDR.uuid
LEFT JOIN 
    (SELECT uuid, SUM(ticket_bonus) AS ticket_bonus
     FROM ticket_bonuses
     WHERE YEARWEEK(FROM_UNIXTIME(timestamp), 1) = YEARWEEK(CURDATE(), 1)
     GROUP BY uuid) TB ON UN.uuid = TB.uuid
WHERE 
    GMC.guild = "Titans Valor"
    AND YEARWEEK(FROM_UNIXTIME(PDR.time), 1) = YEARWEEK(CURDATE(), 1)
    {range_condition}
GROUP BY 
    GMC.name
"""

    res = await Database.fetch(query)

    data = []

    for entry in res:
        name = entry["name"]
        war = do_ticket_math(entry["wars_gain"], 10)
        gxp = do_ticket_math(entry["gxp_gain"], 100_000_000)
        raids = do_ticket_math(entry["raids_gain"], 35)
        bonus = int(entry["ticket_bonus"])
        total = war + gxp + raids + bonus

        if total != 0:
            data.append((name, str(war), str(gxp), str(raids), bonus, total))

    data.sort(key=lambda x: x[-1], reverse=True)

    rows = [[f"{i+1})", name, war, gxp, raids, bonus, total] for i, (name, war, gxp, raids, bonus, total) in enumerate(data)]

    return rows


async def add_ticket_bonus(username: str, value: int) -> str | None:
    uuid = await get_uuid_from_name(username)
    if not uuid:
        return None

    await Database.execute(
        "INSERT INTO ticket_bonuses (uuid, ticket_bonus, timestamp) VALUES (%s, %s, %s)",
        (uuid, value, time.time())
    )
    return uuid


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tickets", description="View or update this week's ticket leaderboard.")
    #@app_commands.describe(
    #    range="Number of days ago, or a range like '0,7', or season name like 'season26' (defaults to most recent Monday)",
    #)
    async def tickets(self, interaction: discord.Interaction): #range: str = None):
        await interaction.response.defer()

        start_timestamp = None

        #if range:
        #    try:
        #        start_timestamp, _ = await get_range_from_string(range)
        #    except Exception:
        #        return await interaction.followup.send(embed=ErrorEmbed("Invalid range format."))

        rows = await get_tickets(start_timestamp)

        if not rows:
            return await interaction.followup.send(embed=ErrorEmbed("No ticket data found."))

        await PaginatedTextTableEmbed.send(interaction, ["", "Name", "War", "GXP", "Raid", "Bonus", "Total"], rows, title="Titans Valor Ticket Leaderboard", rows_per_page=20)



async def setup(bot: commands.Bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)

    existing_global = bot.tree.get_command("tickets")
    if existing_global:
        bot.tree.remove_command("tickets")

    # Manually register the command only for guilds that receive ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.tickets, guild=guild)
