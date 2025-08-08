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
    def __init__(self, bot):
        self.bot = bot

    async def build_profile_image(self, username, uuid, data, warcount, war_ranking, gxp_contrib, gxp_ranking):
        # Define colors and fonts, import image
        black = (0, 0, 0)
        white = (255, 255, 255)
        red = (229, 83, 107)
        green = (87, 234, 128)
        blue = (47, 63, 210)

        name_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 32)
        rank_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 28)
        text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 15)
        stat_text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", 12)

        img = Image.open("assets/profile_template.png")
        draw = ImageDraw.Draw(img)

        # Draw username and rank badge
        offset = 0
        if data.get("supportRank"):
            rank_badge_path = f"assets/icons/ranks/{data['supportRank']}.png"
            if os.path.exists(rank_badge_path):
                rank_badge = Image.open(rank_badge_path)
                img.paste(rank_badge, (21, 25), rank_badge)
                offset = {
                    "vip": 84,
                    "vipplus": 105,
                    "hero": 110,
                    "champion": 175
                }.get(data['supportRank'], 0)
        draw.text((21 + offset, 24), data["username"], white, name_font)

        # Get and draw character model
        tmp_path = f"/tmp/{username}_model.png"
        if not os.path.exists(tmp_path) or time.time() - os.path.getmtime(tmp_path) > 86400:
            headers = {"User-Agent": "valor-bot/1.0"}
            model = await request(f"https://visage.surgeplay.com/bust/{uuid}.png", headers=headers, return_type="image")
            with open(tmp_path, "wb") as f:
                f.write(model)
        model_img = Image.open(tmp_path).resize((203, 190))
        img.paste(model_img, (26, 79), model_img)

        # Draw warcount badge and progress bar
        draw.text((342, 161), war_ranking[0], red, rank_font, anchor="mm")
        draw.text((342, 230), f"{warcount} / {war_ranking[1]}", white, text_font, anchor="ma")
        value = min(round((warcount / war_ranking[1]) * 142), 142)
        draw.rectangle([(269, 221), (value + 269, 224)], red)

        # Draw Guild XP badge and progress bar
        draw.text((542, 161), gxp_ranking[0], green, rank_font, anchor="mm")
        draw.text((542, 230), f"{human_format(gxp_contrib)} / {human_format(gxp_ranking[1])}", white, text_font, anchor="ma")
        value = min(round((gxp_contrib / gxp_ranking[1]) * 142), 142)
        draw.rectangle([(469, 221), (value + 469, 224)], green)

        # Draw coolness bar and label
        recent = await Database.fetch(
            "SELECT COUNT(*) FROM activity_members WHERE uuid=%s AND timestamp >= %s",
            (uuid, int(time.time()) - 7 * 86400)
        )
        cool = min(recent[0]["COUNT(*)"] / 100, 1)
        draw.rectangle([(668, 124), (round(cool * 142) + 668, 127)], blue)
        draw.text((740, 140), f"{round(cool * 100)}% Cool", white, text_font, anchor="ma")

        # Draw currently online and current world
        if data.get("online"):
            draw.text((740, 209), "Player Online:", green, text_font, anchor="ma")
            draw.text((740, 229), data.get("server", "Unknown"), white, text_font, anchor="ma")
        # Draw last seen date
        else:
            if data["lastJoin"]:
                draw.text((740, 209), "Player last seen:", white, text_font, anchor="ma")
                draw.text((740, 229), datetime.fromisoformat(data["lastJoin"][:-1]).strftime("%H:%M  %m/%d/%Y"), white, text_font, anchor="ma")
            else:
                draw.text((740, 209), "Last join date has", white, text_font, anchor="ma")
                draw.text((740, 229), "been API hidden", white, text_font, anchor="ma")

        # Determine top rankings
        rankings = data["ranking"]
        if rankings:
            for rank in dict(rankings):
                if rank in {"hardcoreLegacyLevel"}:
                    rankings.pop(rank)
            top_rank_keys = sorted(rankings, key=rankings.get)[:3]
            top_rankings = {}
            for key in top_rank_keys:
                top_rankings[key] = rankings[key]
            
            # Determine and draw layer's top leaderboard rankings
            for i, key in enumerate(top_rank_keys):
                temp = [s for s in re.split("([A-Z][^A-Z]*)", key) if s]

                rank_badge_link = f"https://cdn.wynncraft.com/nextgen/leaderboard/icons/{temp[0]}.webp?height=50"
                rank_place = rankings[key]
                rank_word_list = []
                for word in temp:
                    if word in {"tcc", "nol", "nog", "tna", "huic", "huich", "hic", "hich"}:
                        rank_word_list.append(word.upper())
                    else:
                        rank_word_list.append(word.title())
                rank = " ".join(rank_word_list)
                wrapper = textwrap.TextWrapper(width=13, max_lines=2, placeholder="") 
                rank = wrapper.wrap(text=rank) 
                
                # Fallback to local icons for gamemodes as they are not easily locateable by CDN
                if temp[0] in {"craftsman", "hunted", "ironman", "hardcore", "ultimate", "huic", "huich", "hic", "hich"}:
                    rank_badge = Image.open(f"assets/icons/gamemodes/{temp[0]}.png")
                else:
                    rank_badge = Image.open(await request(rank_badge_link, return_type="stream"))

                # Finally draw the rankings, their names and their icons
                for x, line in enumerate(rank):
                    draw.text((91+(i*120), 335+(x*20)), line, white, text_font, anchor="ma")
                img.paste(rank_badge, (66+(i*120), 380), rank_badge)
                draw.text((91+(i*120), 445), f"#{rank_place}", white, text_font, anchor="ma")
        else:
            draw.text((207, 389), "All rankings are API hidden.", white, text_font, anchor="ma")

        # Draw player's guild
        offset = 53
        if data["guild"]:
            try:
                # Use custom guild icons for guilds that have provided them. Contact ANO chiefs if you want to get yours added!!
                guild_badge = Image.open(f'assets/icons/guilds/{data["guild"]["prefix"]}.png')
                img.paste(guild_badge, (414, 289), guild_badge)
            except FileNotFoundError:
                offset = 0

            draw.text((505, 380+offset), f'{data["guild"]["rank"]} of', white, text_font, anchor="ma")
            draw.text((505, 400+offset), data["guild"]["name"], white, text_font, anchor="ma")
        else:
            draw.text((505, 390), "No Guild", white, text_font, anchor="ma")


        # Draw other minor player stats
        stats = data["featuredStats"]
        try:
            player_stats = [f'{stats["playtime"]} Hours', 
                        f'{stats["globalData.totalLevel"]} Levels',
                        f'{stats["globalData.mobsKilled"]} Mobs',
                        f'{stats["globalData.chestsFound"]} Chests',
                        f'{stats["globalData.completedQuests"]} Quests']
            i = 0
            for stat in player_stats:
                draw.text((819, 333+(i*29)), stat, white, stat_text_font, anchor="ra")
                i += 1
        except (KeyError, TypeError):
            draw.rectangle([(623, 326), (823, 476)], black) # Draw a very crude black box over the default stat labels
            draw.text((723, 389), "Stats are API hidden.", white, text_font, anchor="ma")


        return img

    @app_commands.command(name="profile", description="Display a profile card for a player")
    @app_commands.describe(username="Username or uuid of targeted player")
    @rate_limit_check()
    async def profile(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()

        # Get player UUID and confirm player exists
        input_type = detect_uuid_or_name(username)
        if input_type == "uuid":
            uuid = username
        elif input_type == "name":
            uuid = await get_uuid_from_name(username)
        else:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid input."))
        
        if not uuid:
            return await interaction.followup.send(embed=ErrorEmbed("Player not found."))

        # Fetch player data from API
        data = await request(f"https://api.wynncraft.com/v3/player/{uuid}")
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching player data."))

        # Get warcount data
        warcount = 0
        res = await Database.fetch("SELECT SUM(warcount) FROM cumu_warcounts WHERE uuid=%s", (uuid,))
        warcount += (res[0]["SUM(warcount)"] if res and res[0]["SUM(warcount)"] is not None else 0)
        war_ranking = get_war_rank(warcount)

        # Get Guild XP data
        res = await Database.fetch("""
            SELECT MAX(xp)
            FROM ((SELECT xp FROM user_total_xps WHERE uuid=%s)
                  UNION ALL
                  (SELECT SUM(delta) FROM player_delta_record WHERE guild='Titans Valor' AND uuid=%s AND label='gu_gxp')) A;
        """, (uuid, uuid))
        gxp_contrib = res[0]["MAX(xp)"] if res and res[0]["MAX(xp)"] else 0
        gxp_ranking = get_xp_rank(gxp_contrib)

        # Build and send final profile image
        img = await self.build_profile_image(username, uuid, data, warcount, war_ranking, gxp_contrib, gxp_ranking)
        if not img:
            return await interaction.followup.send(embed=ErrorEmbed("Hidden player profile."))

        with io.BytesIO() as img_binary:
            img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = File(fp=img_binary, filename="profile.png")

        await interaction.followup.send(file=file)

async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
