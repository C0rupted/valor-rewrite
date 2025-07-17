import discord, logging, aiohttp, time

from discord import app_commands
from discord.ext import commands

from util.embeds import TextTableEmbed, ErrorEmbed


API_URL = "https://athena.wynntils.com/cache/get/serverList"


class Uptime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="uptime", description="Shows the uptime of all active Wynncraft worlds.")
    async def uptime(self, interaction: discord.Interaction):
        await interaction.response.defer()

        url = "https://athena.wynntils.com/cache/get/serverList"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"API returned status {resp.status}")
                    data = await resp.json()

            servers = data.get("servers", {})
            now = int(time.time() * 1000)

            result = []
            for server, info in servers.items():
                ts = info.get("firstSeen")
                if not ts:
                    continue

                uptime_ms = now - ts
                uptime_s = uptime_ms // 1000
                hours, minutes = divmod(uptime_s // 60, 60)
                uptime_str = f"{hours}h {minutes}m"

                player_count = len(info.get("players", []))
                players_str = f"{player_count}/45"

                result.append([server, uptime_str, players_str])

            # Sort by uptime (descending)
            result.sort(key=lambda x: int(x[1].split("h")[0]) * 60 + int(x[1].split("h")[1].split("m")[0]), reverse=True)

            header = ["   World   ", "   Uptime   ", "   Players   "]

            embed = TextTableEmbed(header, result, title="Wynncraft World Uptimes", footer=f"{len(result)} worlds are currently online.")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logging.info(e)
            await interaction.followup.send(embed=ErrorEmbed("Failed to fetch uptime data."))


async def setup(bot):
    await bot.add_cog(Uptime(bot))
