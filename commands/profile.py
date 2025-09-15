import discord, os, time, re, textwrap, io

from discord import app_commands, File
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw

from datetime import datetime
from database import Database

from core.antispam import rate_limit_check
from util.embeds import ErrorEmbed
from util.formatting import human_format
from util.ranks import get_war_rank, get_xp_rank
from util.requests import request
from util.uuid import get_uuid_from_name, detect_uuid_or_name



class Profile(commands.Cog):
    """
    Cog providing /profile command to generate a profile card image for a player with various stats and ranking info.
    """
    def __init__(self, bot):
        self.bot = bot


    async def build_profile_image(
        self, username: str, uuid: str, data: dict, warcount: int,
        war_ranking: tuple, gxp_contrib: int, gxp_ranking: tuple
    ) -> Image.Image:
        """
        Creates a profile card using PIL Image for the player using their stats and rankings.
        """
        # Flag for warning that stats are API hidden
        warn_api_hidden = False

        # Define some common colors for drawing on the image
        black = (0, 0, 0)
        gray = (129, 129, 129)
        white = (255, 255, 255)
        red = (229, 83, 107)
        green = (87, 234, 128)
        blue = (47, 63, 210)

        # Load the fonts used for text rendering on the profile image
        name_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 32)
        rank_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 28)
        text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 15)
        stat_text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 12)

        # Open the base profile template image (PNG with transparent areas)
        img = Image.open("assets/profile_template.png")
        draw = ImageDraw.Draw(img)  # Prepare to draw on the image

        # Draw the username and support rank badge if applicable
        offset = 0  # Used to shift username if rank badge is drawn
        if data.get("supportRank"):
            rank_badge_path = f"assets/icons/ranks/{data['supportRank']}.png"
            # Check if rank badge image exists locally
            if os.path.exists(rank_badge_path):
                rank_badge = Image.open(rank_badge_path)
                # Paste the badge onto the profile image at fixed position with transparency
                img.paste(rank_badge, (21, 25), rank_badge)
                # Offset username x-position based on rank badge width
                offset = {
                    "vip": 84,
                    "vipplus": 105,
                    "hero": 110,
                    "heroplus": 130,
                    "champion": 175
                }.get(data['supportRank'], 0)
        # Draw the username next to the badge (or default position)
        draw.text((21 + offset, 24), data["username"], white, name_font)

        # Prepare to draw the player's character bust model on the profile
        tmp_path = f"/tmp/{username}_model.png"
        # Cache bust model locally for 24 hours to avoid repeated downloads
        if not os.path.exists(tmp_path) or time.time() - os.path.getmtime(tmp_path) > 604800:
            headers = {"User-Agent": "valor-bot/1.0"}
            model = await request(f"https://visage.surgeplay.com/bust/{uuid}.png", headers=headers, return_type="image")
            with open(tmp_path, "wb") as f:
                f.write(model)
        # Open cached model image and resize to fit profile layout
        model_img = Image.open(tmp_path).resize((203, 190))
        # Paste model image onto profile template with transparency mask
        img.paste(model_img, (26, 79), model_img)

        # Draw warcount rank abbreviation (e.g., "A", "B", "C") at fixed position
        draw.text((342, 161), war_ranking[0], red, rank_font, anchor="mm")
        # Draw the warcount progress text (current / max for rank)
        draw.text((342, 230), f"{warcount} / {war_ranking[1]}", white, text_font, anchor="ma")
        # Calculate width of progress bar for warcount (max 142 pixels)
        value = min(round((warcount / war_ranking[1]) * 142), 142)
        # Draw filled rectangle representing warcount progress bar
        draw.rectangle([(269, 221), (value + 269, 224)], red)

        # Gray-out if their warcount tracking is hidden from API.
        if data["restrictions"]["characterDataAccess"]:
            section = img.crop((254, 83, 426, 266))
            section = section.convert("L") # Convert to grayscale
            img.paste(section, (254, 83))
            warn_api_hidden = True

        # Draw guild XP rank abbreviation and progress bar (similar to warcount)
        draw.text((542, 161), gxp_ranking[0], green, rank_font, anchor="mm")
        draw.text((542, 230), f"{human_format(gxp_contrib)} / {human_format(gxp_ranking[1])}", white, text_font, anchor="ma")
        value = min(round((gxp_contrib / gxp_ranking[1]) * 142), 142)
        draw.rectangle([(469, 221), (value + 469, 224)], green)

        # Query recent player activity in last 7 days from database for "coolness"
        recent = await Database.fetch(
            "SELECT COUNT(*) FROM activity_members WHERE uuid=%s AND timestamp >= %s",
            (uuid, int(time.time()) - 7 * 86400)
        )
        # Scale coolness value (clamped to 1 max)
        cool = min(recent[0]["COUNT(*)"] / 100, 1)
        # Draw coolness progress bar (blue)
        draw.rectangle([(668, 124), (round(cool * 142) + 668, 127)], blue)
        # Draw coolness percentage text
        draw.text((740, 140), f"{round(cool * 100)}% Cool", white, text_font, anchor="ma")

        # Draw player online status and current server/world or last seen time
        if data.get("online"):
            # Player is currently online
            draw.text((740, 209), "Player Online:", green, text_font, anchor="ma")
            draw.text((740, 229), data.get("server", "Unknown"), white, text_font, anchor="ma")
        else:
            # Player offline - show last join date or fallback text if hidden by API
            if data["lastJoin"]:
                # Parse ISO datetime string and format for display
                draw.text((740, 209), "Player last seen:", white, text_font, anchor="ma")
                draw.text((740, 229), datetime.fromisoformat(data["lastJoin"][:-1]).strftime("%H:%M  %m/%d/%Y"), white, text_font, anchor="ma")
            else:
                draw.text((740, 209), "Last join date has", gray, text_font, anchor="ma")
                draw.text((740, 229), "been API hidden", gray, text_font, anchor="ma")
                warn_api_hidden = True

        # Extract leaderboard rankings from data and filter out hidden keys
        rankings = data["ranking"]
        if rankings:
            # Remove certain keys from rankings dict
            for rank in dict(rankings):
                if rank in {"hardcoreLegacyLevel"}:
                    rankings.pop(rank)

            # Sort rankings by their values and take top 3 keys
            top_rank_keys = sorted(rankings, key=rankings.get)[:3]
            top_rankings = {}
            for key in top_rank_keys:
                top_rankings[key] = rankings[key]

            # For each top ranking, draw rank name, icon, and rank place number
            for i, key in enumerate(top_rank_keys):
                # Split camelcase rank key into words for formatting
                temp = [s for s in re.split("([A-Z][^A-Z]*)", key) if s]

                # Generate URL for rank badge icon from CDN
                rank_badge_link = f"https://cdn.wynncraft.com/nextgen/leaderboard/icons/{temp[0]}.webp?height=50"
                rank_place = rankings[key]

                # Format rank words, uppercase certain acronyms
                rank_word_list = []
                for word in temp:
                    if word in {"tcc", "nol", "nog", "tna", "huic", "huich", "hic", "hich"}:
                        rank_word_list.append(word.upper())
                    else:
                        rank_word_list.append(word.title())
                rank = " ".join(rank_word_list)

                # Wrap rank text to max 2 lines for neatness
                wrapper = textwrap.TextWrapper(width=13, max_lines=2, placeholder="")
                rank = wrapper.wrap(text=rank)

                # Use local icons for gamemodes that CDN might not have
                if temp[0] in {"craftsman", "hunted", "ironman", "hardcore", "ultimate", "huic", "huich", "hic", "hich"}:
                    rank_badge = Image.open(f"assets/icons/gamemodes/{temp[0]}.png")
                else:
                    # Otherwise, download rank badge icon from CDN
                    rank_badge = Image.open(await request(rank_badge_link, return_type="stream"))

                # Draw each line of rank name text
                for x, line in enumerate(rank):
                    draw.text((91 + (i * 120), 335 + (x * 20)), line, white, text_font, anchor="ma")

                # Paste rank badge icon
                img.paste(rank_badge, (66 + (i * 120), 380), rank_badge)
                # Draw rank placement (e.g. "#1", "#2", etc.)
                draw.text((91 + (i * 120), 445), f"#{rank_place}", white, text_font, anchor="ma")
        else:
            # No rankings available - indicate data is hidden
            draw.text((207, 389), "All rankings are API hidden.", gray, text_font, anchor="ma")
            warn_api_hidden = True

        # Draw player's guild info and guild badge if available
        offset = 53  # Vertical offset for guild rank text if badge exists
        if data["guild"]:
            try:
                # Attempt to load guild badge icon from local assets folder
                guild_badge = Image.open(f'assets/icons/guilds/{data["guild"]["prefix"]}.png')
                img.paste(guild_badge, (414, 289), guild_badge)
            except FileNotFoundError:
                # If no badge icon found, remove vertical offset to align text correctly
                offset = 0

            # Draw guild rank and guild name
            draw.text((505, 380 + offset), f'{data["guild"]["rank"]} of', white, text_font, anchor="ma")
            draw.text((505, 400 + offset), data["guild"]["name"], white, text_font, anchor="ma")
        else:
            # Player is not in a guild - draw placeholder text
            draw.text((505, 390), "No Guild", white, text_font, anchor="ma")

        # Pull player stats from a bunch of different parts of the result while handling hidden stats
        stats = data.get("featuredStats") or {}
        global_data = data.get("globalData") or {}

        playtime = stats.get("playtime") or data.get("playtime")
        total_level = stats.get("globalData.totalLevel") or global_data.get("totalLevel")
        mobs_killed = stats.get("globalData.mobsKilled") or global_data.get("mobsKilled")
        chests_found = stats.get("globalData.chestsFound") or global_data.get("chestsFound")
        completed_quests = stats.get("globalData.completedQuests") or global_data.get("completedQuests")

        # Draw player stats, if found
        if playtime or total_level or mobs_killed or chests_found or completed_quests:
            player_stats = [
                f'{playtime} Hours',
                f'{total_level} Levels',
                f'{mobs_killed} Mobs',
                f'{chests_found} Chests',
                f'{completed_quests} Quests'
            ]
            # Draw each stat on the right side of the profile
            i = 0
            for stat in player_stats:
                draw.text((819, 333 + (i * 29)), stat, white, stat_text_font, anchor="ra")
                i += 1
        else:
            # If any stats missing or data hidden, draw black rectangle and fallback message
            draw.rectangle([(623, 326), (823, 476)], black)  # Overwrite default stat labels
            draw.text((723, 389), "Stats are API hidden.", gray, text_font, anchor="ma")
            warn_api_hidden = True

        # Return the completed PIL image object
        return img, warn_api_hidden


    @app_commands.command(name="profile", description="Display a profile card for a player")
    @app_commands.describe(username="Username or uuid of targeted player")
    @rate_limit_check()
    async def profile(self, interaction: discord.Interaction, username: str):
        # Defer response because processing may take time (e.g., image building)
        await interaction.response.defer()

        # Determine if input is a UUID or username string
        input_type = detect_uuid_or_name(username)
        if input_type == "uuid":
            uuid = username
        elif input_type == "name":
            uuid = await get_uuid_from_name(username)
        else:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid input."))

        # If no UUID found for player, return error message
        if not uuid:
            return await interaction.followup.send(embed=ErrorEmbed("Player not found."))

        # Fetch player data from external API (Wynncraft)
        data = await request(f"https://api.wynncraft.com/v3/player/{uuid}?fullResult")
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching player data."))
        guild = await request(f"https://api.wynncraft.com/v3/guild/prefix/{data["guild"]["prefix"]}") if data.get("guild") else None

        # Query database for player's total warcount
        res = await Database.fetch("SELECT SUM(warcount) FROM cumu_warcounts WHERE uuid=%s", (uuid,))
        warcount = res[0]["SUM(warcount)"] if res and res[0]["SUM(warcount)"] is not None else 0
        # Determine player's war rank based on warcount
        war_ranking = get_war_rank(warcount)

        # Query database for guild XP contribution (max of total xp and guild XP deltas)
        res = await Database.fetch("""
            SELECT MAX(xp)
            FROM ((SELECT xp FROM user_total_xps WHERE uuid=%s)
                  UNION ALL
                  (SELECT SUM(delta) FROM player_delta_record WHERE uuid=%s AND label='gu_gxp')) A;
        """, (uuid, uuid))
        res_contrib = res[0]["MAX(xp)"] if res and res[0]["MAX(xp)"] else 0
        api_contrib = guild["members"][data["guild"]["rank"].lower()][data["username"]]["contributed"] if data.get("guild") else 0
        gxp_contrib = max(res_contrib, api_contrib)
        # Determine guild XP rank based on contribution
        gxp_ranking = get_xp_rank(gxp_contrib)

        # Build the profile image asynchronously using gathered data
        img, warn_api_hidden = await self.build_profile_image(username, uuid, data, warcount, war_ranking, gxp_contrib, gxp_ranking)
        if not img:
            return await interaction.followup.send(embed=ErrorEmbed("Hidden player profile."))

        # Convert PIL Image to in-memory binary PNG for Discord upload
        with io.BytesIO() as img_binary:
            img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = File(fp=img_binary, filename="profile.png")

            message = "Unhide your API!!!!!!!!!" if warn_api_hidden else ""

            # Send the profile image as a file attachment in the Discord followup response
            await interaction.followup.send(file=file, content=message)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
