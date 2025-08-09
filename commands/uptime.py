import discord, time

from discord import app_commands
from discord.ext import commands

from core.antispam import rate_limit_check
from util.embeds import TextTableEmbed
from util.requests import request


# URL for the Wynncraft uptime API that returns server status info
UPTIME_API_URL = "https://athena.wynntils.com/cache/get/serverList"



class Uptime(commands.Cog):
    """
    Cog providing the /uptime command to get a list of online Wyncraft worlds and their uptimes.
    """
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="uptime", description="Shows the uptime of all active Wynncraft worlds.")
    @rate_limit_check()
    async def uptime(self, interaction: discord.Interaction):
        """
        Slash command to display the uptime and player count of all active Wynncraft worlds.

        Workflow:
        - Fetches live server data from the Wynncraft Athena uptime API.
        - Calculates the uptime duration for each server.
        - Collects player counts.
        - Sorts servers by uptime descending.
        - Displays the data as a formatted text table embed.
        """
        # Defer interaction response to allow time for API fetch and processing
        await interaction.response.defer()

        # Make asynchronous GET request to the uptime API endpoint
        data = await request(UPTIME_API_URL)

        # Extract the dictionary of servers from the API response
        servers = data.get("servers", {})

        # Current timestamp in milliseconds for uptime calculation
        now = int(time.time() * 1000)

        result = []
        for server, info in servers.items():
            # Get the timestamp when the server was first seen online
            ts = info.get("firstSeen")
            if not ts:
                # Skip servers without firstSeen timestamp
                continue

            # Calculate uptime in milliseconds, then convert to seconds
            uptime_ms = now - ts
            uptime_s = uptime_ms // 1000

            # Convert uptime seconds into hours and minutes
            hours, minutes = divmod(uptime_s // 60, 60)
            uptime_str = f"{hours}h {minutes}m"

            # Count the number of players currently on this server
            player_count = len(info.get("players", []))
            players_str = f"{player_count}/45"

            # Append server info row: [World name, uptime string, player count string]
            result.append([server, uptime_str, players_str])

        # Sort results descending by uptime in minutes (convert 'Xh Ym' to total minutes)
        result.sort(key=lambda x: int(x[1].split("h")[0]) * 60 + int(x[1].split("h")[1].split("m")[0]), reverse=True)

        # Column headers for the embed table
        headers = ["World", "Uptime", "Players"]

        # Create a TextTableEmbed with the headers, rows, and a footer with count of worlds online
        embed = TextTableEmbed(headers, result, title="Wynncraft World Uptimes", footer=f"{len(result)} worlds are currently online.")

        # Send the embed as a follow-up message
        await interaction.followup.send(embed=embed)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Uptime(bot))
