import discord, requests
from discord import app_commands
from discord.ext import commands

from util.embeds import ErrorEmbed
from util.mappings import EMOJI_MAP, ITEM_TO_EMOJI_MAP, ASPECT_TO_EMOJI_MAP


class Pools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    LOOT_POOL_NAME_MAP = {
        "silent_expanse": "Silent Expanse",
        "canyon_of_the_lost": "Canyon of the Lost",
        "corkus": "Corkus",
        "sky_islands": "Sky Islands",
        "molten_heights": "Molten Heights"
    }

    LOOT_POOL_API_MAP = {
        "silent_expanse": "SE",
        "canyon_of_the_lost": "Canyon",
        "corkus": "Corkus",
        "sky_islands": "Sky",
        "molten_heights": "Molten"
    }

    ASPECT_POOL_NAME_MAP = {
        "tna": "The Nameless Anomaly",
        "tcc": "The Canyon Colossus",
        "nol": "Nexus of Light",
        "notg": "Nest of The Grootslangs"
    }

    ASPECT_POOL_API_MAP = {
        "tna": "TNA",
        "tcc": "TCC",
        "nol": "NOL",
        "notg": "NOTG"
    }

    BASE_URL = "https://nori.fish"
    TOKEN_URL = f"{BASE_URL}/api/tokens"
    LOOTPOOL_URL = f"{BASE_URL}/api/lootpool"
    ASPECTPOOL_URL = f"{BASE_URL}/api/aspects"
    LOOTRUN_ICON_URL = "https://static.wikia.nocookie.net/wynncraft_gamepedia_en/images/f/f0/LootrunUpdateIcon.png/revision/latest"
    ASPECT_ICON_URL = "https://nori.fish/resources/aspect.gif"

    # === Loot Pool ===

    async def fetch_data(self, url):
        session = requests.Session()
        token_response = session.get(self.TOKEN_URL)
        token_response.raise_for_status()

        csrf_token = session.cookies.get("csrf_token")
        headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf_token}

        response = session.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    async def build_loot_embed(self, pool_key=None):
        data = (await self.fetch_data(self.LOOTPOOL_URL))["Loot"]

        # All lootpools overview
        if pool_key is None:
            embed = discord.Embed(title="Loot Pool Overview", color=discord.Colour.from_rgb(74, 86, 219))
            for key, name in self.LOOT_POOL_NAME_MAP.items():
                api_name = self.LOOT_POOL_API_MAP[key]
                pool = data.get(api_name)
                if not pool:
                    continue

                field = ""
                shiny = pool.get("Shiny")
                mythics = pool.get("Mythic", [])

                if shiny:
                    icon = EMOJI_MAP[ITEM_TO_EMOJI_MAP[shiny["Item"]]]
                    field += f"- {EMOJI_MAP['shiny']}{icon} **Shiny** {shiny['Item']} (Tracker: {shiny['Tracker']})\n"
                for item in mythics:
                    icon = EMOJI_MAP[ITEM_TO_EMOJI_MAP[item]]
                    field += f"- {icon} {item}\n"

                embed.add_field(name=f"{name} Mythics", value=field or "None", inline=False)

            embed.set_thumbnail(url=self.LOOTRUN_ICON_URL)
            return embed

        # Detailed view for specific camp
        api_name = self.LOOT_POOL_API_MAP[pool_key]
        pool = data.get(api_name)
        if not pool:
            return ErrorEmbed(f"Loot pool data for {api_name} not found.")

        embed = discord.Embed(title=f"Loot Pool: {api_name}", color=discord.Colour.from_rgb(74, 86, 219))
        shiny = pool.pop("Shiny", None)
        mythics = pool.pop("Mythic", [])

        text = ""
        if shiny:
            icon = EMOJI_MAP[ITEM_TO_EMOJI_MAP[shiny['Item']]]
            text += f"- {EMOJI_MAP['shiny']}{icon} **Shiny** {shiny['Item']} (Tracker: {shiny['Tracker']})\n"
        for item in mythics:
            icon = EMOJI_MAP[ITEM_TO_EMOJI_MAP[item]]
            text += f"- {icon} {item}\n"
        embed.add_field(name="Mythics", value=text or "None", inline=False)

        for rarity, items in pool.items():
            field = "\n".join(f"- {item}" for item in items)
            embed.add_field(name=rarity, value=field or "None", inline=False)

        embed.set_thumbnail(url=self.LOOTRUN_ICON_URL)
        return embed

    class LootPoolSelect(discord.ui.Select):
        def __init__(self, cog: "Pools"):
            self.cog = cog
            options = [discord.SelectOption(label=name, value=key) for key, name in cog.LOOT_POOL_NAME_MAP.items()]
            super().__init__(placeholder="Choose a loot pool...", options=options)

        async def callback(self, interaction: discord.Interaction):
            embed = await self.cog.build_loot_embed(self.values[0])
            await interaction.response.edit_message(embed=embed, view=self.view)

    class LootPoolView(discord.ui.View):
        def __init__(self, cog: "Pools"):
            super().__init__()
            self.add_item(Pools.LootPoolSelect(cog))

    @app_commands.command(name="lootpool", description="View the current loot pool for mythics and more")
    async def lootpool(self, interaction: discord.Interaction):
        embed = await self.build_loot_embed()
        view = self.LootPoolView(self)
        await interaction.response.send_message(embed=embed, view=view)

    # === Aspect Pool ===

    async def build_aspect_embed(self, raid_key=None):
        data = await self.fetch_data(self.ASPECTPOOL_URL)

        if raid_key is None:
            embed = discord.Embed(title="Aspect Pool Overview", color=discord.Colour.from_rgb(255, 71, 77))
            for key, name in self.ASPECT_POOL_NAME_MAP.items():
                raid = data["Loot"][self.ASPECT_POOL_API_MAP[key]]
                text = ""
                for item in raid["Mythic"]:
                    icon = EMOJI_MAP[ASPECT_TO_EMOJI_MAP[data["Icon"][item]]]
                    text += f"- {icon} {item}\n"
                embed.add_field(name=f"{name} Mythic Aspects", value=text or "None", inline=False)
            embed.set_thumbnail(url=self.ASPECT_ICON_URL)
            return embed

        pool_key = self.ASPECT_POOL_API_MAP[raid_key]
        raid_data = data["Loot"].get(pool_key)
        if not raid_data:
            return ErrorEmbed(f"Aspect data for {pool_key} not found.")

        embed = discord.Embed(title=f"Aspect Pool: {self.ASPECT_POOL_NAME_MAP[raid_key]}", color=discord.Colour.from_rgb(255, 71, 77))
        for rarity in ("Mythic", "Fabled", "Legendary"):
            items = raid_data.get(rarity, [])
            field = "\n".join(f"- {EMOJI_MAP[ASPECT_TO_EMOJI_MAP[data['Icon'][item]]]} {item}" for item in items)
            embed.add_field(name=f"{rarity} Aspects", value=field or "None", inline=False)

        embed.set_thumbnail(url=self.ASPECT_ICON_URL)
        return embed

    class AspectPoolSelect(discord.ui.Select):
        def __init__(self, cog: "Pools"):
            self.cog = cog
            options = [discord.SelectOption(label=name, value=key) for key, name in cog.ASPECT_POOL_NAME_MAP.items()]
            super().__init__(placeholder="Choose an aspect pool...", options=options)

        async def callback(self, interaction: discord.Interaction):
            embed = await self.cog.build_aspect_embed(self.values[0])
            await interaction.response.edit_message(embed=embed, view=self.view)

    class AspectPoolView(discord.ui.View):
        def __init__(self, cog: "Pools"):
            super().__init__()
            self.add_item(Pools.AspectPoolSelect(cog))

    @app_commands.command(name="aspectpool", description="View current aspect pool for raids")
    async def aspectpool(self, interaction: discord.Interaction):
        embed = await self.build_aspect_embed()
        view = self.AspectPoolView(self)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    cog = Pools(bot)
    await bot.add_cog(cog)


