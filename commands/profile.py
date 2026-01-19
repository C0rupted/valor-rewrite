import discord, os, time, re, textwrap, io, tempfile, logging, asyncio

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


    async def build_profile_image(
        self, username: str, uuid: str, data: dict, warcount: int,
        war_ranking: tuple, gxp_contrib: int, gxp_ranking: tuple
    ) -> Image.Image:
        warn_api_hidden = False

        black = (0, 0, 0)
        gray = (129, 129, 129)
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
                    "heroplus": 130,
                    "champion": 175
                }.get(data['supportRank'], 0)
        draw.text((21 + offset, 24), data["username"], white, name_font)

        tmp_path = os.path.join(tempfile.gettempdir(), f"{username}_model.png")
        if not os.path.exists(tmp_path) or time.time() - os.path.getmtime(tmp_path) > 604800:
            headers = {"User-Agent": "valor-bot/1.0"}
            model = await request(f"https://visage.surgeplay.com/bust/{uuid}.png", headers=headers, return_type="image")
            with open(tmp_path, "wb") as f:
                f.write(model)
        model_img = Image.open(tmp_path).resize((203, 190))
        img.paste(model_img, (26, 79), model_img)

        draw.text((342, 161), war_ranking[0], red, rank_font, anchor="mm")
        draw.text((342, 230), f"{warcount} / {war_ranking[1]}", white, text_font, anchor="ma")
        value = min(round((warcount / war_ranking[1]) * 142), 142)
        draw.rectangle([(269, 221), (value + 269, 224)], red)

        if data["restrictions"]["characterDataAccess"]:
            section = img.crop((254, 83, 426, 266))
            section = section.convert("L")
            img.paste(section, (254, 83))
            warn_api_hidden = True

        draw.text((542, 161), gxp_ranking[0], green, rank_font, anchor="mm")
        draw.text((542, 230), f"{human_format(gxp_contrib)} / {human_format(gxp_ranking[1])}", white, text_font, anchor="ma")
        value = min(round((gxp_contrib / gxp_ranking[1]) * 142), 142)
        draw.rectangle([(469, 221), (value + 469, 224)], green)

        recent = await Database.fetch(
            "SELECT COUNT(*) FROM activity_members WHERE uuid=%s AND timestamp >= %s",
            (uuid, int(time.time()) - 7 * 86400)
        )
        cool = min(recent[0]["COUNT(*)"] / 100, 1)
        draw.rectangle([(668, 124), (round(cool * 142) + 668, 127)], blue)
        draw.text((740, 140), f"{round(cool * 100)}% Cool", white, text_font, anchor="ma")

        if data.get("online"):
            draw.text((740, 209), "Player Online:", green, text_font, anchor="ma")
            draw.text((740, 229), data.get("server", "Unknown"), white, text_font, anchor="ma")
        else:
            if data["lastJoin"]:
                draw.text((740, 209), "Player last seen:", white, text_font, anchor="ma")
                draw.text((740, 229), datetime.fromisoformat(data["lastJoin"][:-1]).strftime("%H:%M  %m/%d/%Y"), white, text_font, anchor="ma")
            else:
                draw.text((740, 209), "Last join date has", gray, text_font, anchor="ma")
                draw.text((740, 229), "been API hidden", gray, text_font, anchor="ma")
                warn_api_hidden = True

        rankings = data["ranking"]
        if rankings:
            for rank in dict(rankings):
                if rank in {"hardcoreLegacyLevel"}:
                    rankings.pop(rank)

            top_rank_keys = sorted(rankings, key=rankings.get)[:3]
            top_rankings = {}
            for key in top_rank_keys:
                top_rankings[key] = rankings[key]

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

                if temp[0] in {"craftsman", "hunted", "ironman", "hardcore", "ultimate", "huic", "huich", "hic", "hich"}:
                    rank_badge = Image.open(f"assets/icons/gamemodes/{temp[0]}.png")
                else:
                    rank_badge = Image.open(await request(rank_badge_link, return_type="stream"))

                for x, line in enumerate(rank):
                    draw.text((91 + (i * 120), 335 + (x * 20)), line, white, text_font, anchor="ma")

                img.paste(rank_badge, (66 + (i * 120), 380), rank_badge)
                draw.text((91 + (i * 120), 445), f"#{rank_place}", white, text_font, anchor="ma")
        else:
            draw.text((207, 389), "All rankings are API hidden.", gray, text_font, anchor="ma")
            warn_api_hidden = True

        offset = 53
        if data["guild"]:
            try:
                guild_badge = Image.open(f'assets/icons/guilds/{data["guild"]["prefix"]}.png')
                if guild_badge.mode != 'RGBA':
                    guild_badge = guild_badge.convert('RGBA')
                guild_badge = guild_badge.resize((90, 90))
                await asyncio.sleep(0.005)
                img.paste(guild_badge, (459, 329), guild_badge)
            except Exception as e:
                logging.warning(f"Failed to load guild icon for {data['guild']['prefix']}: {type(e).__name__}: {e}")
                offset = 0

            draw.text((505, 380 + offset), f'{data["guild"]["rank"]} of', white, text_font, anchor="ma")
            draw.text((505, 400 + offset), data["guild"]["name"], white, text_font, anchor="ma")
        else:
            draw.text((505, 390), "No Guild", white, text_font, anchor="ma")

        stats = data.get("featuredStats") or {}
        global_data = data.get("globalData") or {}

        playtime = stats.get("playtime") or data.get("playtime")
        total_level = stats.get("globalData.totalLevel") or global_data.get("totalLevel")
        mobs_killed = stats.get("globalData.mobsKilled") or global_data.get("mobsKilled")
        chests_found = stats.get("globalData.chestsFound") or global_data.get("chestsFound")
        completed_quests = stats.get("globalData.completedQuests") or global_data.get("completedQuests")

        if playtime or total_level or mobs_killed or chests_found or completed_quests:
            player_stats = [
                f'{playtime} Hours',
                f'{total_level} Levels',
                f'{mobs_killed} Mobs',
                f'{chests_found} Chests',
                f'{completed_quests} Quests'
            ]
            i = 0
            for stat in player_stats:
                draw.text((819, 333 + (i * 29)), stat, white, stat_text_font, anchor="ra")
                i += 1
        else:
            draw.rectangle([(623, 326), (823, 476)], black)
            draw.text((723, 389), "Stats are API hidden.", gray, text_font, anchor="ma")
            warn_api_hidden = True

        return img, warn_api_hidden


    @app_commands.command(name="profile", description="Display a profile card for a player")
    @app_commands.describe(username="Username or uuid of targeted player")
    @rate_limit_check()
    async def profile(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()

        input_type = detect_uuid_or_name(username)
        if input_type == "uuid":
            uuid = username
        elif input_type == "name":
            uuid = await get_uuid_from_name(username)
        else:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid input."))

        if not uuid:
            return await interaction.followup.send(embed=ErrorEmbed("Player not found."))

        data = await request(f"https://api.wynncraft.com/v3/player/{uuid}?fullResult")
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching player data."))
        guild = await request(f"https://api.wynncraft.com/v3/guild/prefix/{data['guild']['prefix']}") if data.get("guild") else None

        res = await Database.fetch("SELECT SUM(warcount) FROM cumu_warcounts WHERE uuid=%s", (uuid,))
        warcount = res[0]["SUM(warcount)"] if res and res[0]["SUM(warcount)"] is not None else 0
        war_ranking = get_war_rank(warcount)

        res = await Database.fetch("""
            SELECT MAX(xp)
            FROM ((SELECT xp FROM user_total_xps WHERE uuid=%s)
                  UNION ALL
                  (SELECT SUM(delta) FROM player_delta_record WHERE uuid=%s AND label='gu_gxp')) A;
        """, (uuid, uuid))
        res_contrib = res[0]["MAX(xp)"] if res and res[0]["MAX(xp)"] else 0
        api_contrib = guild["members"][data["guild"]["rank"].lower()][data["username"]]["contributed"] if data.get("guild") else 0
        gxp_contrib = max(res_contrib, api_contrib)
        gxp_ranking = get_xp_rank(gxp_contrib)

        img, warn_api_hidden = await self.build_profile_image(username, uuid, data, warcount, war_ranking, gxp_contrib, gxp_ranking)
        if not img:
            return await interaction.followup.send(embed=ErrorEmbed("Hidden player profile."))

        with io.BytesIO() as img_binary:
            img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = File(fp=img_binary, filename="profile.png")

            message = "Unhide your API!!!!!!!!!" if warn_api_hidden else ""

            await interaction.followup.send(file=file, content=message)

async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
