import logging, discord, requests

from datetime import datetime, timedelta
from discord.ext import commands, tasks

from core.config import Config
from util.mappings import FFA_TERRITORIES


WYNN_API_URL = "https://api.wynncraft.com/v3/guild/list/territory"
ATHENA_API_URL = "https://athena.wynntils.com/cache/get/territoryList"



def format_timedelta(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    periods = [
        ('d', 86400),
        ('h', 3600),
        ('m', 60),
        ('s', 1)
    ]
    
    parts = []
    for name, size in periods:
        if seconds >= size:
            value, seconds = divmod(seconds, size)
            parts.append(f"{value}{name}")
            
    # Return top two, or top one if only one exists
    return " ".join(parts[:2])



def fetch_territory_data() -> dict:
    try:
        # Try fetching from Athena API first
        response = requests.get(ATHENA_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "territories" in data:
            return data["territories"]
        else:
            logging.warning("Territory Tracker: Athena API error")
    except requests.RequestException as e:
        logging.error(f"Error fetching territory data from Athena API: {e}")

    # Fallback to Wynn API
    try:
        response = requests.get(WYNN_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        output = {}
        for territory, info in data.items():
            terr_info = {}
            terr_info["territory"] = territory
            terr_info["guild"] = info["guild"]["name"]
            terr_info["guildPrefix"] = info["guild"]["prefix"]
            terr_info["acquired"] = info["acquired"]

            output[territory] = terr_info
        
        return output
    except requests.RequestException as e:
        logging.error(f"Error fetching territory data from Wynn API: {e}")
        return {}


def create_terrchange_embed(old_territory, new_territory, for_ano: bool = False):
    embed = discord.Embed(
        title=f"Territory Captured: {new_territory['territory']}", 
        color=0x007bff  # light, neutral blue color
    )
    embed.add_field(name="Previous Owner", value=f"{old_territory['guild']} ({old_territory['guildPrefix']})", inline=True)
    embed.add_field(name="New Owner", value=f"{new_territory['guild']} ({new_territory['guildPrefix']})", inline=True)
    
    # add blank field line separator
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    held_time = datetime.fromisoformat(new_territory["acquired"]) - datetime.fromisoformat(old_territory["acquired"])
    held_time_str = format_timedelta(held_time)
    embed.add_field(name="Held for", value=held_time_str, inline=True)
    embed.add_field(name="FFA Territory", value="Yes" if new_territory["territory"] in FFA_TERRITORIES else "No", inline=True)

    # add blank field line separator for balancing spacing
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.set_footer(text=f"Acquired on: {datetime.fromisoformat(new_territory['acquired']).strftime('%d/%m/%Y %I:%M %p')}")
    return embed



class TerritoryTrackerService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.territory_data = fetch_territory_data()  # Store the latest territory data
        # Start the repeating weekly task
        self.terryitory_tracker_loop.start()


    def cog_unload(self):
        # Cancel the task when the cog is unloaded (bot shutdown/reload)
        self.terryitory_tracker_loop.cancel()


    @tasks.loop(minutes=1)  # Repeat every minute to check for updates
    async def terryitory_tracker_loop(self):
        updated_data = fetch_territory_data()  # Update territory data every minute
        # find all territories that have changed guild ownership
        changed_territories = []
        for territory, info in updated_data.items():
            if self.territory_data[territory]["guild"] != info["guild"]:
                changed_territories.append(info)

        if changed_territories:
            channel = self.bot.get_channel(Config.TERRITORY_TRACKER_CHANNEL_ID)
            ano_channel = self.bot.get_channel(Config.ANO_TERRITORY_TRACKER_CHANNEL_ID)
            for territory in changed_territories:
                for_ano = territory["guildPrefix"] == "ANO" or self.territory_data[territory["territory"]]["guildPrefix"] == "ANO"
                embed = create_terrchange_embed(self.territory_data[territory["territory"]], territory, for_ano)
                if for_ano:
                    await ano_channel.send(embed=embed)
                
                await channel.send(embed=embed)
            
        self.territory_data = updated_data  # Update the stored data for the next loop iteration


    @terryitory_tracker_loop.before_loop
    async def before_ticket_post_loop(self):
        pass





# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(TerritoryTrackerService(bot))
