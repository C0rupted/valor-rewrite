import discord,  datetime, time, uuid
from discord import app_commands, Embed
from discord.ext import commands

from core.antispam import rate_limit_check
from core.config import config
from database import Database
from util.embeds import ErrorEmbed
from util.requests import request
from util.uuid import get_uuid_from_name, detect_uuid_or_name, get_name_from_uuid


class Sus(commands.Cog):
    """
    Cog providing /sus command for checking user suspiciousness.
    """
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sus", description="Checks if a Wynncraft player is suspicious.")
    @rate_limit_check()
    async def sus(self, interaction: discord.Interaction, username: str):
        """
        Slash command to check if a Wynncraft player is suspicious based on various criteria.

        Args:
            interaction (discord.Interaction): The interaction object from Discord.
            username (str): The Minecraft username to check.
        """
        # Defer the response as this may take some time to fetch data
        await interaction.response.defer()

        # Get the UUID and username
        input_type = detect_uuid_or_name(username)
        if input_type == "uuid":
            id = username
            name = await get_name_from_uuid(username)
        elif input_type == "name":
            id = await get_uuid_from_name(username)
            name = username
        else:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid input."))

        # If no UUID found for player, return error message
        if not id:
            return await interaction.followup.send(embed=ErrorEmbed("Player not found."))

        # Convert UUID string (without dashes) to a standard dashed UUID string
        dashed_uuid = str(uuid.UUID(hex=id))

        # Fetch player data from Hypixel API using the UUID
        hypixel_data = await request(f"https://api.hypixel.net/player?uuid={id}", headers={"API-Key": config.HYPIXEL_API_KEY})
        hypixel_join = None
        try:
            # If successful and player data exists, get first login timestamp (convert ms to seconds)
            if hypixel_data["success"] and hypixel_data["player"] and hypixel_data["player"]["firstLogin"]:
                hypixel_join = float(int(hypixel_data["player"]["firstLogin"] / 1000))
            else:
                # If player data missing or unsuccessful, inform user of Hypixel API issue
                return await interaction.followup.send(embed=ErrorEmbed("Player has never logged onto Hypixel before?! That's a bit sus..."))
        except KeyError:
            # Catch key errors from malformed response and notify
            return await interaction.followup.send(embed=ErrorEmbed("Player has never logged onto Hypixel before?! That's a bit sus..."))

        # Fetch Wynncraft player data from Wynncraft API using dashed UUID
        wynn_data = await request(f"https://api.wynncraft.com/v3/player/{dashed_uuid}?fullResult")

        # Check if 'username' key exists in response to verify successful fetch
        try:
            if "username" not in wynn_data:
                # If missing, respond with error about Wynncraft API
                return await interaction.followup.send(embed=ErrorEmbed("Wynn API Issue"))
        except TypeError:
            return await interaction.followup.send(embed=ErrorEmbed("Player has never logged onto Wynncraft."))

        try:
            # Extract player's Wynncraft join date (YYYY-MM-DD)
            wynn_join = wynn_data["firstJoin"].split("T")[0]

            # Convert join date string to a UNIX timestamp (seconds since epoch)
            wynn_join_timestamp = time.mktime(datetime.datetime.strptime(wynn_join, "%Y-%m-%d").timetuple())

            # Extract player's support rank (e.g., VIP, Champion, etc.)
            wynn_rank = wynn_data["supportRank"]

            # Sum total level across all characters
            try:
                wynn_level = sum([character["level"] for _, character in wynn_data["characters"].items()])
            except AttributeError:
                wynn_level = "API Hidden"

            # Extract total playtime (hours)
            wynn_playtime = wynn_data["playtime"]

            # Extract total completed quests
            wynn_quest = wynn_data["globalData"]["completedQuests"]
        except KeyError:
            # If any of the above keys are missing, profile may be hidden
            return await interaction.followup.send(embed=ErrorEmbed("Hidden player profile."))

        # Determine earliest join time between Hypixel and Wynncraft for suspicion check
        first_seen = min(hypixel_join, wynn_join_timestamp) if hypixel_join else wynn_join_timestamp

        # Format the earliest join time as a human-readable date string
        first_seen_time = datetime.date.fromtimestamp(first_seen).strftime("%Y-%m-%d")

        # Calculate suspiciousness percentage based on first seen date.
        # Players seen less than 3 years ago (94672800 seconds) are more suspicious.
        first_seen_sus = round(max(0, (time.time() - first_seen - 94672800) * -1) * 100 / 94672800, 1)

        # Calculate suspiciousness based on Wynncraft join date (less than 2 years)
        wynn_join_sus = round(max(0, (time.time() - wynn_join_timestamp - 63072000) * -1) * 100 / 63072000, 1)

        # Suspiciousness if Wynncraft total level is below 210
        try:
            wynn_level_sus = round(max(0, (wynn_level - 210) * -1) * 100 / 210, 1)
        except:
            wynn_level_sus = 100.0

        # Suspiciousness if playtime is below 800 hours
        wynn_playtime_sus = round(max(0, (wynn_playtime - 800) * -1) * 100 / 800, 1)

        # Suspiciousness if completed quests are below 150
        wynn_quest_sus = round(max(0, (wynn_quest - 150) * -1) * 100 / 150, 1)

        # Query the database to check if the player is blacklisted
        query = "SELECT * FROM player_blacklist WHERE uuid=%s"
        blacklisted = await Database.fetch(query, (dashed_uuid))
        if blacklisted:
            # If blacklisted, set flag and maximum suspiciousness score
            blacklisted = "**BLACKLISTED**"
            blacklisted_sus = 100.0
        else:
            blacklisted = "False"
            blacklisted_sus = 0

        # Assign suspiciousness score based on support rank
        if wynn_rank in ["veteran", "champion", "hero", "heroplus", "vipplus"]:
            wynn_rank_sus = 0.0  # trusted ranks => no suspicion
        elif wynn_rank == "vip":
            wynn_rank_sus = 25.0  # some suspicion for vip
        else:
            wynn_rank_sus = 50.0  # unknown or no rank => more suspicion

        # Calculate overall suspiciousness as average of all metrics
        overall_sus = round(
            (first_seen_sus + wynn_join_sus + wynn_level_sus + wynn_playtime_sus + wynn_quest_sus + wynn_rank_sus) / 6, 2
        )

        # Build Discord embed with suspiciousness info
        embed = Embed(
            title=f"Suspiciousness of {name}: {overall_sus}%",
            description="The rating is based on the following components:",
            color=discord.Color.green()
        )

        # Add thumbnail with player's skin bust
        embed.set_thumbnail(url=f"https://visage.surgeplay.com/bust/512/{id}.png?y=-40")

        # Add fields showing each metric and their suspiciousness score
        embed.add_field(name="Wynncraft Join Date", value=f"{wynn_join}\n{wynn_join_sus}%", inline=True)
        embed.add_field(name="Wynncraft Playtime", value=f"{wynn_playtime} hours\n{wynn_playtime_sus}%", inline=True)
        embed.add_field(name="Wynncraft Level", value=f"{wynn_level}\n{wynn_level_sus}%", inline=True)
        embed.add_field(name="Wynncraft Quests", value=f"{wynn_quest}\n{wynn_quest_sus}%", inline=True)
        embed.add_field(name="Wynncraft Rank", value=f"{wynn_rank}\n{wynn_rank_sus}%", inline=True)
        embed.add_field(name="Minecraft First Seen", value=f"{first_seen_time}\n{first_seen_sus}%", inline=True)

        # If blacklisted, override suspiciousness and color with warning
        if blacklisted != "False":
            overall_sus = 100.0
            embed.color = discord.Color.red()
            embed.title = f"Suspiciousness of {name}: {overall_sus}% \n ⚠ Player is blacklisted ⚠"
            embed.add_field(name="Blacklisted?", value=f"{blacklisted}\n{blacklisted_sus}%", inline=True)

        # Send the constructed embed in response to the interaction
        await interaction.followup.send(embed=embed)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Sus(bot))
