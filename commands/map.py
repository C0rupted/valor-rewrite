import discord, json, logging, io

from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from core.antispam import rate_limit_check
from util.embeds import ErrorEmbed
from util.guilds import guild_names_from_tags
from util.requests import request


# Load predefined map regions with coordinates and labels for cropping/autocomplete
with open("assets/map_regions.json") as f:
    map_regions = json.load(f)



class Map(commands.Cog):
    """
    Cog providing the /map command to display the live Wynncraft territory map.

    Supports optional filtering by guild tags and zooming into specific regions/zones.
    Draws territories with guild colors, outlines, labels, and trading route connections.
    """
    def __init__(self, bot):
        self.bot = bot


    def to_full_map_coord(self, x_ingame, y_ingame, map_width, map_height):
        """
        Convert in-game coordinates to pixel coordinates on the full map image.

        Args:
            x_ingame (float): X coordinate in-game.
            y_ingame (float): Y coordinate in-game.
            map_width (int): Width of the map image in pixels.
            map_height (int): Height of the map image in pixels.

        Returns:
            tuple: (x_canvas, y_canvas) pixel coordinates on the map image.
        """
        x_canvas = (x_ingame + 2382) * map_width / 4034
        y_canvas = (y_ingame + 6572) * map_height / 6414
        return x_canvas, y_canvas


    def draw_text_with_outline(self, draw, position, text, font, fill, outline_color=(0, 0, 0), outline_width=1):
        """
        Draw text on the image with an outline to improve readability.

        This draws the text multiple times shifted by outline_width in all directions
        before drawing the main text on top.

        Args:
            draw (ImageDraw.Draw): PIL drawing context.
            position (tuple): (x, y) coordinates to draw the text.
            text (str): The string to draw.
            font (ImageFont.FreeTypeFont): Font to use.
            fill (tuple): RGB color for the text fill.
            outline_color (tuple): RGB color for the outline.
            outline_width (int): Width of the outline in pixels.
        """
        x, y = position
        y_pad = -2  # Adjust vertical position for alignment
        # Draw outline by drawing text shifted in all surrounding pixels except center
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy + y_pad), text, font=font, fill=outline_color)
        # Draw main text on top
        draw.text((x, y + y_pad), text, font=font, fill=fill)

    def hex_to_rgb(self, hex_color, fallback=(136, 136, 136)):
        """
        Convert a hex color string to an RGB tuple.

        Supports 6-digit, 3-digit, and truncated hex strings (pads with zeros).

        Args:
            hex_color (str): Hex string, e.g. "#ff0000" or "f00".
            fallback (tuple): RGB tuple to return if conversion fails.

        Returns:
            tuple: (R, G, B) color values.
        """
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            elif len(hex_color) == 3:
                return tuple(int(hex_color[i]*2, 16) for i in range(3))
            elif len(hex_color) < 6:
                # Pad short hex with zeros for safety
                padded = (hex_color + "0"*6)[:6]
                return tuple(int(padded[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            logging.warning(f"Invalid color code: #{hex_color}")
        return fallback


    @app_commands.command(name="map", description="Show the live Wynncraft territory map, optionally filtered by guild or zone.")
    @app_commands.describe(guild="Filter by guild tags (comma-separated)", zone="Optional region/zone name to crop to")
    @rate_limit_check()
    async def map(self, interaction: discord.Interaction, guild: str = None, zone: str = None):
        """
        Main command handler for the territory map.

        Optionally filters territories by guild tag(s) and crops the map to a specific zone.

        Workflow:
        - Parse filters.
        - Fetch live territory and guild data from Athena API.
        - Load static map assets.
        - Convert territory coordinates to canvas coordinates.
        - Draw territory rectangles colored by guild.
        - Draw labels with outlined text.
        - Draw trading route connections as lines.
        - Compose all layers into final image.
        - Crop to zone if specified.
        - Send the generated image as a Discord file.

        Args:
            interaction (discord.Interaction): Command interaction.
            guild (str, optional): Comma-separated guild tag filters.
            zone (str, optional): Zone name to crop to.
        """
        await interaction.response.defer()

        # Normalize guild tags to lowercase for filtering
        guild_tags = [tag.strip().lower() for tag in guild.split(",")] if guild else []

        # Validate zone filter if provided
        if zone:
            if zone not in map_regions:
                return await interaction.followup.send("Invalid zone.", ephemeral=True)

        # Fetch live territory and guild color data from Wynntils Athena API
        try:
            terr_res = await request("https://athena.wynntils.com/cache/get/territoryList")
            guild_colors_res = await request("https://athena.wynntils.com/cache/get/guildListWithColors")
            guild_color_lookup = {entry["_id"]: entry["color"] for entry in guild_colors_res.values()}
        except:
            return await interaction.followup.send("Athena is down.", ephemeral=True)

        # Load trading route connections (static data)
        with open("assets/terr_conns.json") as f:
            terr_conns = json.load(f)

        # Load base map image and font for labels
        main_map = Image.open("assets/main_map.png")
        font = ImageFont.truetype("assets/MinecraftRegular.ttf", 16)
        map_width, map_height = main_map.size

        # Create separate transparent layers for drawing base, territories, and labels
        base = Image.new("RGBA", main_map.size)
        terr_layer = Image.new("RGBA", main_map.size)
        label_layer = Image.new("RGBA", main_map.size)
        draw_base = ImageDraw.Draw(base)
        draw_territory = ImageDraw.Draw(terr_layer)
        draw_label = ImageDraw.Draw(label_layer)

        centers = {}      # Store center coordinates of each territory (for connections)
        terr_owners = {}  # Store owner prefix for each territory (for filtering connections)

        # Calculate centers of each territory rectangle in canvas coordinates
        for name, data in terr_res["territories"].items():
            loc = data["location"]
            x1, y1 = self.to_full_map_coord(loc["startX"], loc["startZ"], map_width, map_height)
            x2, y2 = self.to_full_map_coord(loc["endX"], loc["endZ"], map_width, map_height)
            cx = (min(x1, x2) + max(x1, x2)) / 2
            cy = (min(y1, y2) + max(y1, y2)) / 2
            centers[name] = (cx, cy)
        
        # Keep track of the positions of upper-left most territory and lower-right most territory 
        # if certain guilds have been specified, so rest of the map can be cropped out.
        if guild_tags:
            min_x, min_y = float("inf"), float("inf")
            max_x, max_y = float("-inf"), float("-inf")

        # Draw each territory as a colored rectangle with label
        for name, data in terr_res["territories"].items():
            loc = data["location"]
            prefix = data["guildPrefix"]

            # Skip if filtering by guild and this territory is not owned by one of the guild tags
            if guild_tags and prefix.lower() not in guild_tags:
                continue

            terr_owners[name] = prefix

            # Determine fill and border colors: guild color or fallback gray
            color = data.get("guildColor") or guild_color_lookup.get(data["guild"], "#888888")
            rgb = self.hex_to_rgb(color) if prefix else (255, 255, 255)
            fill = rgb + (90,)      # semi-transparent fill
            border = rgb + (255,)   # opaque border

            # Convert territory bounding box to canvas pixels
            x1, y1 = self.to_full_map_coord(loc["startX"], loc["startZ"], map_width, map_height)
            x2, y2 = self.to_full_map_coord(loc["endX"], loc["endZ"], map_width, map_height)
            left, right = sorted([x1, x2])
            top, bottom = sorted([y1, y2])
            cx, cy = (left + right) / 2, (top + bottom) / 2

            # Track bounds if guild filtering is active
            if guild_tags:
                min_x = min(min_x, left)
                min_y = min(min_y, top)
                max_x = max(max_x, right)
                max_y = max(max_y, bottom)

            # Draw filled rectangle on territory layer
            draw_territory.rectangle([left, top, right, bottom], fill=fill)
            # Draw label background rectangles with black outline and guild color border
            draw_label.rectangle([left-1, top-1, right+1, bottom+1], outline=(0, 0, 0), width=3)
            draw_label.rectangle([left, top, right, bottom], outline=border, width=2)

            # Compute text size and draw guild prefix centered with outline for readability
            bbox = draw_label.textbbox((0, 0), prefix, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            self.draw_text_with_outline(draw_label, (cx - tw/2, cy - th/2), prefix, font, fill=border)

        # Draw trading route connections as lines between territory centers
        for start, targets in terr_conns.items():
            center_start = centers.get(start)
            if not center_start:
                continue
            for target in targets.get("Trading Routes", []):
                if target not in centers:
                    continue

                # If filtering by guild, only draw connections where both start and target territories belong to filtered guilds
                if guild_tags and (terr_owners.get(start) not in guild_tags or terr_owners.get(target) not in guild_tags):
                    continue

                # Draw a dark line on the base layer connecting the two territories
                draw_base.line([center_start, centers[target]], fill=(20, 20, 20), width=2)

        # Compose final image by layering: base map -> base lines -> territories -> labels
        composed = Image.alpha_composite(main_map.convert("RGBA"), base)
        composed = Image.alpha_composite(composed, terr_layer)
        final = Image.alpha_composite(composed, label_layer)

        # Crop final image to specified guild's territories if specified
        if guild_tags and not zone:
            if min_x != float("inf"):
                final = final.crop((min_x - 50, min_y - 50, max_x + 50, max_y + 50))
            else:
                return await interaction.followup.send(embed=ErrorEmbed(
                        f"Specified guild{"s are" if len(guild_tags) > 1 else " is"} not currently on the map."
                    )
                )

        # Crop final image to specified zone region if requested
        if zone and zone in map_regions:
            reg = map_regions[zone]["pos"]
            x1, y1 = self.to_full_map_coord(reg[0], reg[1], map_width, map_height)
            x2, y2 = self.to_full_map_coord(reg[2], reg[3], map_width, map_height)
            # Add 50 pixel padding around crop region for context
            final = final.crop((x1 - 50, y1 - 50, x2 + 50, y2 + 50))

        
        # Save image to bytes buffer and send as Discord file.
        with io.BytesIO() as img_binary:
            final.save(img_binary, 'PNG')
            img_binary.seek(0)
            await interaction.followup.send(file=discord.File(fp=img_binary, filename="map.png"))


    @map.autocomplete("zone")
    async def guild_settings_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """
        Autocomplete handler for the zone parameter in the map command.

        Matches user input against known zone keys and labels for suggestions.
        """
        autocomplete = []
        current = current.lower()

        for zone in map_regions:
            name = map_regions[zone]["label"]

            # Suggest zones where the current input matches zone key or label (case-insensitive)
            if (current in zone) or (current in name):
                autocomplete.append(app_commands.Choice(name=name.title(), value=zone))

        return autocomplete



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Map(bot))
