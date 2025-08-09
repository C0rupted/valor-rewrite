import discord, logging

from discord import app_commands
from discord.ext import commands

from core.config import config
from database import Database
from util.embeds import ErrorEmbed, PaginatedTextTableEmbed
from util.mappings import EMOJI_MAP
from util.ranges import get_range_from_string, get_current_season


class OceanTrials(commands.Cog):
    """
    Cog providing /oceantrials command to calculate Ocean Trials LE payouts.

    Payouts are calculated based on war counts within a given season range.
    Provides individual player payouts or an aggregated guild leaderboard.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    # Define milestones as (wars threshold, LE reward) pairs
    MILESTONES = [
        (50, 5), (100, 5), (150, 5), (200, 5), (250, 5),
        (300, 10), (400, 10), (500, 10), (600, 10), (700, 10),
        (800, 10), (900, 10), (1000, 15)
    ]

    def le_for_wars(self, wars: int) -> int:
        """
        Calculate total LE payout for a given number of wars.

        LE is sum of all milestone rewards up to the number of wars,
        plus an additional 1 LE for every 10 wars beyond that.

        Args:
            wars (int): Number of wars fought.

        Returns:
            int: Total LE payout.
        """
        # Sum milestone rewards for all milestones reached
        le = sum(reward for threshold, reward in self.MILESTONES if wars >= threshold)
        # Add 1 LE for every 10 wars (additional bonus)
        le += wars // 10
        return le


    def next_milestone(self, wars: int):
        """
        Find the next milestone that hasn't been reached yet.

        Args:
            wars (int): Current war count.

        Returns:
            tuple or None: (milestone_threshold, reward) or None if all reached.
        """
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
        """
        Main command handler for Ocean Trials.

        If a username is provided, shows individual player's wars and LE payout.
        Otherwise, shows a leaderboard for Titans Valor guild members.

        Args:
            interaction (discord.Interaction): Interaction context.
            name (str, optional): Player username.
            season (str, optional): Season number as string.
        """
        await interaction.response.defer()

        # If no season provided, use the current season
        if not season:
            season = await get_current_season()
            # Extract just the number (strip "season" prefix)
            season = season[6:]

        # Validate season number input
        try:
            season_num = int(season)
        except ValueError:
            return await interaction.followup.send(embed=ErrorEmbed("You must provide a valid season number."))

        # Warning about payout differences in older seasons
        extra_warning = "The payouts of older seasons used to be different " if season_num < 20 else ""

        # Get UNIX timestamp range for the season to filter warcount data
        range_result = await get_range_from_string(f"season{season}", max_allowed_range=None)
        if not range_result:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching season range."))
        left, right = range_result

        if name:
            # Individual player query: sum of warcount diffs for username in season range
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

            # Build embed showing wars and LE payout with milestone info
            embed = discord.Embed(
                title=f"Ocean Trials payouts for {name}",
                color=discord.Color.teal(),
                description=f"Wars in range: **{wars}**\nLE from milestones: **{total_le}{EMOJI_MAP['le']}**"
            )
            if milestone:
                embed.add_field(name="Next milestone", value=f"{milestone[0]} wars ({milestone[1]}{EMOJI_MAP['le']})", inline=False)
                embed.add_field(name="Wars to next milestone", value=f"{max(0, milestone[0] - wars)}", inline=False)
            else:
                embed.add_field(name="Milestones", value="All milestones reached.", inline=False)
            embed.set_footer(text=extra_warning)
            return await interaction.followup.send(embed=embed)

        # Guild-wide query: total wars per member of Titans Valor in the season range
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

        # Prepare rows filtering out entries with 0 LE payout
        rows = [(entry["name"], int(entry["wars"])) for entry in res if self.le_for_wars(int(entry["wars"])) > 0]

        if not rows:
            return await interaction.followup.send(embed=ErrorEmbed("No war data in the selected range."))

        # Format rows as (name, wars, LE string)
        rows = [(name, str(wars), f"{self.le_for_wars(wars)} LE") for name, wars in rows]

        # Send paginated embed table leaderboard
        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "Wars", "LE"],
            rows,
            title=f"Ocean Trials payouts for Season {season_num}",
            footer=extra_warning,
            color=discord.Color.teal(),
            rows_per_page=20
        )



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = OceanTrials(bot)
    await bot.add_cog(cog)

    # Remove global command registration if present
    existing_global = bot.tree.get_command("oceantrials")
    if existing_global:
        bot.tree.remove_command("oceantrials")

    # Register command only for specific guild IDs configured for ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.oceantrials, guild=guild)
