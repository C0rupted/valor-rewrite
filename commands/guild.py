import discord, datetime, logging

from discord.ext import commands
from discord import app_commands

from util.embeds import ErrorEmbed, TextTableEmbed, PaginatedTextTableEmbed, PaginatedFieldedTextTableEmbed
from util.guilds import guild_name_from_tag
from util.mappings import RANK_SYMBOL_MAP
from util.requests import request



async def get_data(guild_tag: str):
    name = await guild_name_from_tag(guild_tag)
    return await request(f"https://api.wynncraft.com/v3/guild/{name}")


async def get_online(data, return_embed: bool = False):
    if "members" not in data:
        return None

    online_members = [
        (name, RANK_SYMBOL_MAP.get(rank, rank), member["server"])
        for rank, v in data["members"].items()
        if rank != "total"
        for name, member in v.items()
        if member["online"]
    ]

    if not online_members:
        return "There are no members online."

    embed = TextTableEmbed(
            [" Name ", " Rank ", " World "],
            sorted(online_members, key=lambda x: len(x[1]), reverse=True),
            title=f"Members of {data["name"]} online ({len(online_members)})",
            color=0x7785cc,
        )

    if return_embed: return embed
    else: return embed.description


class GuildCommands(commands.GroupCog, name="guild"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(name="overview", description="View basic guild info")
    @app_commands.describe(guild="The guild prefix of the target guild")
    async def overview(self, interaction: discord.Interaction, guild: str):
        await interaction.response.defer()

        data = await get_data(guild)

        desc = f"""```properties
Name: {data["name"]} [{data["prefix"]}]
Level: {data["level"]} ({data["xpPercent"]}%)
Owner: {list(data["members"]["owner"])[0]}
Members: {data["members"]["total"]}
Territories: {data["territories"]}
War Count: {data["wars"]}
Created: {datetime.datetime.fromisoformat(data["created"][:-1]).strftime("%m/%d/%Y  %H:%M")}
```"""
        online_desc = await get_online(data)
        
        embed = discord.Embed(title=f"{data['name']}: Overview", description=desc, color=0x7785cc)
        embed.add_field(name="Online Members", value=online_desc)

        return await interaction.followup.send(embed=embed)


    @app_commands.command(name="online", description="View online players of the guild")
    @app_commands.describe(guild="The guild prefix of the target guild")
    async def online(self, interaction: discord.Interaction, guild: str):
        await interaction.response.defer()

        data = await get_data(guild)
        embed = await get_online(data, return_embed=True)

        await interaction.followup.send(embed=embed)


    @app_commands.command(name="members", description="View a list of all players in a guild")
    async def members(self, interaction: discord.Interaction, guild: str):
        await interaction.response.defer()

        data = await get_data(guild)
        sections = {}

        for rank, players in data["members"].items():
            if rank == "total":
                continue

            rows = []
            for name, details in players.items():
                joined = datetime.datetime.fromisoformat(details["joined"][:-1]).strftime("%m/%d/%Y")
                rows.append([name, joined])

            section_title = f"{rank.capitalize()} ({len(rows)})"
            sections[section_title] = rows

        await PaginatedFieldedTextTableEmbed.send(
            interaction,
            ["Name", "Joined"],
            sections,
            title=f"{data['name']}: Members",
            color=discord.Color.blue(),
            rows_per_page=20
        )


    @app_commands.command(name="gxp", description="View the GXP contributions of each player in a guild")
    async def gxp(self, interaction: discord.Interaction, guild: str):
        await interaction.response.defer()

        data = await get_data(guild)
        rows = []

        for rank in data["members"]:
            if rank == "total": continue
            for player, player_data in data["members"][rank].items():
                rows.append([player, player_data["contributed"]])
        
        rows = sorted(rows, key=lambda x: x[1], reverse=True)

        for row in rows: rows[rows.index(row)][1] = f"{rows[rows.index(row)][1]:,} "

        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "XP"],
            rows,
            title=f"{data['name']}: GXP Contributions",
            color=discord.Color.blue(),
            rows_per_page=20
        )



async def setup(bot: commands.Bot):
    await bot.add_cog(GuildCommands(bot))
