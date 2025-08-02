import discord, logging

from discord import app_commands
from discord.ext import commands

from core.config import config
from database import Database
from util.embeds import ErrorEmbed, PaginatedTextTableEmbed
from util.mappings import EMOJI_MAP
from util.ranges import get_range_from_string, get_current_season



class OceanTrials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    MILESTONES = [
        (50, 5), (100, 5), (150, 5), (200, 5), (250, 5),
        (300, 10), (400, 10), (500, 10), (600, 10), (700, 10),
        (800, 10), (900, 10), (1000, 15)
    ]

    def le_for_wars(self, wars: int) -> int:
        le = sum(r for t, r in self.MILESTONES if wars >= t)
        le += wars // 10
        return le

    def next_milestone(self, wars: int):
        for threshold, reward in self.MILESTONES:
            if wars < threshold:
                return threshold, reward
        return None

    @app_commands.command(name="oceantrials", description="View Ocean Trials payout for a player or for Titans Valor.")
    @app_commands.describe(
        name="Username of a specific player (for individual payout)",
        season="Season number (e.g., 25, 26, 27)"
    )
    async def oceantrials(self, interaction: discord.Interaction, name: str = None, season: str = None):
        await interaction.response.defer()
        
        if not season:
            season = await get_current_season()
            season = season[6:]

        try: season_num = int(season)
        except ValueError: return await interaction.followup.send(embed=ErrorEmbed("You must provide a valid season number."))

        extra_warning = "The payouts of older seasons used to be different " if season_num < 20 else ""

        range_result = await get_range_from_string(f"season{season}")
        if not range_result:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching season range."))
        left, right = range_result

        if name:
            query = """
                SELECT SUM(warcount_diff) FROM delta_warcounts
                LEFT JOIN uuid_name ON uuid_name.uuid = delta_warcounts.uuid
                WHERE UPPER(uuid_name.name) = UPPER(%s)
                AND delta_warcounts.time BETWEEN %s AND %s
            """
            res = await Database.fetch(query, (name, left, right))

            wars = int(res[0]["SUM(warcount_diff)"]) if res and res[0]["SUM(warcount_diff)"] else 0
            total_le = self.le_for_wars(wars)
            milestone = self.next_milestone(wars)

            embed = discord.Embed(
                title=f"Ocean Trials payouts for {name}",
                color=discord.Color.teal(),
                description=f"Wars in range: **{wars}**\nLE from milestones: **{total_le}{EMOJI_MAP["le"]}**"
            )
            if milestone:
                embed.add_field(name="Next milestone", value=f"{milestone[0]} wars ({milestone[1]}{EMOJI_MAP["le"]})", inline=False)
                embed.add_field(name="Wars to next milestone", value=f"{max(0, milestone[0] - wars)}", inline=False)
            else:
                embed.add_field(name="Milestones", value="All milestones reached.", inline=False)
            embed.set_footer(text=extra_warning)
            return await interaction.followup.send(embed=embed)

        query = f"""
            SELECT uuid_name.name, SUM(warcount_diff) as wars
            FROM delta_warcounts
            LEFT JOIN player_stats ON player_stats.uuid = delta_warcounts.uuid
            LEFT JOIN uuid_name ON uuid_name.uuid = delta_warcounts.uuid
            WHERE player_stats.guild = 'Titans Valor'
              AND delta_warcounts.time BETWEEN %s AND %s
            GROUP BY uuid_name.name
            HAVING wars > 0
            ORDER BY wars DESC
        """
        res = await Database.fetch(query, (left, right))

        rows = [(entry["name"], int(entry["wars"])) for entry in res if self.le_for_wars(int(entry["wars"])) > 0]

        if not rows:
            return await interaction.followup.send(embed=ErrorEmbed("No war data in the selected range."))

        rows = [(name, str(wars), f"{self.le_for_wars(wars)} LE") for name, wars in rows]

        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "Wars", "LE"],
            rows,
            title=f"Ocean Trials payouts for Season {season_num}",
            footer=extra_warning,
            color=discord.Color.teal(),
            rows_per_page=20
        )

async def setup(bot: commands.Bot):
    cog = OceanTrials(bot)
    await bot.add_cog(cog)

    existing_global = bot.tree.get_command("oceantrials")
    if existing_global:
        bot.tree.remove_command("oceantrials")

    # Manually register the command only for guilds that receive ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.oceantrials, guild=guild)
