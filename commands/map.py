import discord, json, logging

from discord import app_commands
from discord.ext import commands

from PIL import Image, ImageDraw, ImageFont
from util.requests import request

with open("assets/map_regions.json") as f:
    map_regions = json.load(f)

class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def to_full_map_coord(self, x_ingame, y_ingame, map_width, map_height):
        x_canvas = (x_ingame + 2382) * map_width / 4034
        y_canvas = (y_ingame + 6572) * map_height / 6414
        return x_canvas, y_canvas

    def draw_text_with_outline(self, draw, position, text, font, fill, outline_color=(0, 0, 0), outline_width=1):
        x, y = position
        y_pad = -2
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy + y_pad), text, font=font, fill=outline_color)
        draw.text((x, y + y_pad), text, font=font, fill=fill)

    def hex_to_rgb(self, hex_color, fallback=(136, 136, 136)):
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            elif len(hex_color) == 3:
                return tuple(int(hex_color[i]*2, 16) for i in range(3))
            elif len(hex_color) < 6:
                padded = (hex_color + "0"*6)[:6]
                return tuple(int(padded[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            logging.warning(f"Invalid color code: #{hex_color}")
        return fallback


    @app_commands.command(name="map", description="Show the live Wynncraft territory map, optionally filtered by guild or zone.")
    @app_commands.describe(guild="Filter by guild tags (comma-separated)", zone="Optional region/zone name to crop to")
    async def map(self, interaction: discord.Interaction, guild: str = None, zone: str = None):
        await interaction.response.defer()

        guild_tags = [tag.strip().lower() for tag in guild.split(",")] if guild else []
        if zone:
            if not zone in map_regions:
                return await interaction.followup.send("Invalid zone.", ephemeral=True)

        try:
            terr_res = await request("https://athena.wynntils.com/cache/get/territoryList")
            guild_colors_res = await request("https://athena.wynntils.com/cache/get/guildListWithColors")
            guild_color_lookup = {entry["_id"]: entry["color"] for entry in guild_colors_res.values()}
        except:
            return await interaction.followup.send("Athena is down.", ephemeral=True)

        with open("assets/terr_conns.json") as f:
            terr_conns = json.load(f)

        main_map = Image.open("assets/main_map.png")
        font = ImageFont.truetype("assets/MinecraftRegular.ttf", 16)
        map_width, map_height = main_map.size

        base = Image.new("RGBA", main_map.size)
        terr_layer = Image.new("RGBA", main_map.size)
        label_layer = Image.new("RGBA", main_map.size)
        draw_base = ImageDraw.Draw(base)
        draw_territory = ImageDraw.Draw(terr_layer)
        draw_label = ImageDraw.Draw(label_layer)

        centers = {}
        terr_owners = {}

        for name, data in terr_res["territories"].items():
            loc = data["location"]
            x1, y1 = self.to_full_map_coord(loc["startX"], loc["startZ"], map_width, map_height)
            x2, y2 = self.to_full_map_coord(loc["endX"], loc["endZ"], map_width, map_height)
            cx = (min(x1, x2) + max(x1, x2)) / 2
            cy = (min(y1, y2) + max(y1, y2)) / 2
            centers[name] = (cx, cy)

        for name, data in terr_res["territories"].items():
            loc = data["location"]
            prefix = data["guildPrefix"]
            if guild_tags and not prefix.lower() in guild_tags:
                continue

            terr_owners[name] = prefix
            color = data.get("guildColor") or guild_color_lookup.get(data["guild"], "#888888")
            rgb = self.hex_to_rgb(color) if prefix else (255, 255, 255)
            fill = rgb + (90,)
            border = rgb + (255,)

            x1, y1 = self.to_full_map_coord(loc["startX"], loc["startZ"], map_width, map_height)
            x2, y2 = self.to_full_map_coord(loc["endX"], loc["endZ"], map_width, map_height)
            left, right = sorted([x1, x2])
            top, bottom = sorted([y1, y2])
            cx, cy = (left + right) / 2, (top + bottom) / 2

            draw_territory.rectangle([left, top, right, bottom], fill=fill)
            draw_label.rectangle([left-1, top-1, right+1, bottom+1], outline=(0, 0, 0), width=3)
            draw_label.rectangle([left, top, right, bottom], outline=border, width=2)

            bbox = draw_label.textbbox((0, 0), prefix, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            self.draw_text_with_outline(draw_label, (cx - tw/2, cy - th/2), prefix, font, fill=border)

        for start, targets in terr_conns.items():
            center_start = centers.get(start)
            if not center_start:
                continue
            for target in targets.get("Trading Routes", []):
                if target not in centers:
                    continue
                if guild_tags and (terr_owners.get(start) not in guild_tags or terr_owners.get(target) not in guild_tags):
                    continue
                draw_base.line([center_start, centers[target]], fill=(20, 20, 20), width=2)

        composed = Image.alpha_composite(main_map.convert("RGBA"), base)
        composed = Image.alpha_composite(composed, terr_layer)
        final = Image.alpha_composite(composed, label_layer)

        if zone:
            if zone in map_regions:
                reg = map_regions[zone]["pos"]
                x1, y1 = self.to_full_map_coord(reg[0], reg[1], map_width, map_height)
                x2, y2 = self.to_full_map_coord(reg[2], reg[3], map_width, map_height)
                final = final.crop((x1 - 50, y1 - 50, x2 + 50, y2 + 50))

        path = "/tmp/map.png"
        final.save(path)
        await interaction.followup.send(file=discord.File(path))
    
    
    @map.autocomplete("zone")
    async def guild_settings_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        autocomplete = []
        current = current.lower()

        for zone in map_regions:
            name = map_regions[zone]["label"]

            if (current in zone) or (current in name):
                autocomplete.append(app_commands.Choice(name=name.title(), value=zone))

        return autocomplete

async def setup(bot):
    await bot.add_cog(Map(bot))
