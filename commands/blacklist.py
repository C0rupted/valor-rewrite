import discord, time

from discord import app_commands
from discord.ext import commands
from datetime import datetime

from core.config import config
from database import Database
from util.embeds import ErrorEmbed, InfoEmbed, PaginatedTextTableEmbed
from util.roles import is_ANO_titan_rank, is_ANO_chief
from util.guilds import player_guild_from_uuid, player_guilds_from_uuids
from util.requests import request
from util.uuid import get_name_from_uuid, get_uuid_from_name, get_names_from_uuids


class Blacklist(commands.GroupCog, name="blacklist"):
    """
    Cog containing commands for ANO blacklist.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(description="List all players on the blacklist.")
    async def list(self, interaction: discord.Interaction):
        """
        Lists all players currently on the blacklist, along with:
        - Current guild
        - Date they were added
        """
        await interaction.response.defer()

        # Fetch all blacklisted players (UUID + timestamp)
        res = await Database.fetch("SELECT uuid, timestamp FROM player_blacklist")

        uuids = []
        dates = {}

        # Store UUIDs and convert timestamps to human-readable format
        for result in res:
            uuids.append(result["uuid"])
            dates[result["uuid"]] = datetime.fromtimestamp(result["timestamp"]).strftime("%d-%m-%Y")

        # Retrieve player names and current guilds in bulk
        player_names = await get_names_from_uuids(uuids)
        player_guilds = await player_guilds_from_uuids(uuids)

        rows = []
        for uuid in uuids:
            try:
                rows.append((
                    player_names[uuid],
                    player_guilds[uuid],
                    dates[uuid]
                ))
            except KeyError:
                # Many UUIDs are broken; skip them silently to avoid spamming logs
                pass

        # Display blacklist in a paginated table
        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "Current Guild", "Date Added"],
            rows,
            title="Blacklist",
            color=discord.Color.dark_red(),
            rows_per_page=15
        )


    @app_commands.command(description="Add a player to the blacklist.")
    @app_commands.describe(
        username="The player's username",
        reason="The reason for blacklisting"
    )
    async def add(self, interaction: discord.Interaction, username: str, reason: str = "No reason given"):
        """
        Adds a player to the blacklist. Requires user to have ANO Titan rank or higher (unless TESTING mode is enabled).

        Steps:
        1. Validate user permissions.
        2. Ensure username format is valid.
        3. Convert username to UUID.
        4. Insert/replace entry in blacklist table.
        """
        # Permission check
        if not (is_ANO_titan_rank(interaction.user) or is_ANO_chief(interaction.user)) and not config.TESTING:
            return await interaction.response.send_message(
                embed=ErrorEmbed("No Permissions"), ephemeral=True
            )

        # Quick input validation
        if "-" in username:
            return await interaction.response.send_message(
                embed=ErrorEmbed("Invalid input"), ephemeral=True
            )

        # Convert username to UUID
        try:
            uuid = await get_uuid_from_name(username)
        except:
            return await interaction.response.send_message(
                embed=ErrorEmbed("Can't add player (Player doesn't exist?)"), ephemeral=True
            )

        timestamp = int(time.time())

        # Add player to database (REPLACE will overwrite if they already exist)
        await Database.execute(
            "REPLACE INTO player_blacklist VALUES (%s, %s, %s)",
            (uuid, reason, timestamp)
        )

        # Confirmation embed
        embed = InfoEmbed(
            title=f"Added {username} to the blacklist",
            description=f"Reason: {reason}\nTime added: <t:{timestamp}:F>",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)


    @app_commands.command(description="Remove a player from the blacklist.")
    @app_commands.describe(username="The player's username")
    async def remove(self, interaction: discord.Interaction, username: str):
        """
        Removes a player from the blacklist. Requires user to have ANO Titan rank or higher (unless TESTING mode is enabled).

        Steps:
        1. Check permissions.
        2. Validate input.
        3. Look up UUID from username.
        4. Delete from database.
        """
        # Permission check
        if not (is_ANO_titan_rank(interaction.user) or is_ANO_chief(interaction.user)) and not config.TESTING:
            return await interaction.response.send_message(
                embed=ErrorEmbed("No Permissions"), ephemeral=True
            )

        # Quick input validation
        if "-" in username:
            return await interaction.response.send_message(
                embed=ErrorEmbed("Invalid input"), ephemeral=True
            )

        # Convert username to UUID and delete from database
        uuid = await get_uuid_from_name(username)
        await Database.execute(
            "DELETE FROM player_blacklist WHERE uuid = %s",
            (uuid,)
        )

        # Confirmation embed
        embed = InfoEmbed(
            title=f"Deleted {username}",
            description="Removed player from the blacklist",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)


    @app_commands.command(description="Search the blacklist for a player.")
    @app_commands.describe(username="The player's username or UUID")
    async def search(self, interaction: discord.Interaction, username: str):
        """
        Searches the blacklist for a specific player.

        Accepts either:
        - Username
        - UUID

        Shows:
        - Reason for blacklist
        - Current guild (database or Wynncraft API)
        - Time added
        - UUID
        """
        await interaction.response.defer()

        # Convert username to UUID if needed
        uuid = await get_uuid_from_name(username) if "-" not in username else username
        username = await get_name_from_uuid(uuid)

        # Look up blacklist entry
        res = await Database.fetchrow(
            "SELECT reason, timestamp FROM player_blacklist WHERE uuid = %s",
            (uuid)
        )
        if not res:
            return await interaction.followup.send(embed=ErrorEmbed("No results found"))

        reason = res["reason"]
        timestamp = res["timestamp"]

        # Get guild from database or Wynncraft API
        db_guild = await player_guild_from_uuid(uuid)
        guild = db_guild or (await request(f"https://api.wynncraft.com/v3/player/{uuid}"))

        if isinstance(guild, dict):
            if "error" in guild:
                guild = "No Wynncraft data"
            else:
                guild = guild.get("guild", {}).get("name", "Unknown")

        # Build search result embed
        embed = discord.Embed(
            title="Blacklist Search Result",
            description=username,
            color=discord.Color.dark_red()
        )

        embed.set_footer(text="Ask any Titan+ with proof to add someone to the blacklist")
        embed.set_thumbnail(url=f"https://visage.surgeplay.com/bust/{uuid}")
        embed.add_field(name="Reason", value=reason or "No reason", inline=False)
        embed.add_field(name="Current Guild", value=guild)
        embed.add_field(name="Time Added", value=f"<t:{timestamp}:F>")
        embed.add_field(name="UUID", value=uuid, inline=False)

        await interaction.followup.send(embed=embed)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))
