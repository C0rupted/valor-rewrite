import discord, datetime

from discord.ext import commands
from discord import app_commands

from core.antispam import rate_limit_check
from database import Database
from core.settings import SettingsManager
from util.embeds import ErrorEmbed, TextTableEmbed, PaginatedTextTableEmbed, PaginatedFieldedTextTableEmbed
from util.guilds import guild_name_from_tag
from util.mappings import RANK_SYMBOL_MAP
from util.requests import request



async def get_data(guild: str, interaction: discord.Interaction):
    """
    Fetch guild data from the Wynncraft API.

    If no guild is provided, fetches default guild info set for the discord server settings.
    Attempts to resolve guild names and prefixes for accurate API querying.
    """
    if not guild:
        guild_name = SettingsManager("guild", interaction.guild.id).get("guild_name")
        guild_tag = SettingsManager("guild", interaction.guild.id).get("guild_tag")

        if not (guild_name and guild_tag):
            return "warn"  # Warn caller that default guild info is missing
        return await request(f"https://api.wynncraft.com/v3/guild/{guild_name}")

    name = await guild_name_from_tag(guild) or guild
    res = await request(f"https://api.wynncraft.com/v3/guild/{name}")
    if not res:
        # Try querying by prefix if guild name lookup failed
        res = await request(f"https://api.wynncraft.com/v3/guild/prefix/{guild}")

    return res


async def get_online(data, return_embed: bool = False):
    """
    Process guild data to get a list or embed of online members.

    Returns either a simple string table or a Discord Embed depending on `return_embed`.
    """
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
        if return_embed:
            return discord.Embed(
                title=f"Members of {data['name']} online (0)",
                description="```isbl\nThere are no members online.\n```",
                color=0x7785cc
            )
        else:
            return "```isbl\nThere are no members online.\n```"

    embed = TextTableEmbed(
        ["Name", "Rank", "World"],
        sorted(online_members, key=lambda x: len(x[1]), reverse=True),
        title=f"Members of {data['name']} online ({len(online_members)})",
        color=0x7785cc,
    )

    if return_embed:
        return embed
    else:
        return embed.description



class GuildCommands(commands.GroupCog, name="guild"):
    """
    Group cog containing guild-related slash commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(name="overview", description="View basic guild info")
    @app_commands.describe(guild="The guild name or prefix of the target guild")
    async def overview(self, interaction: discord.Interaction, guild: str = None):
        """
        Display an overview of guild stats including level, owner, member count, territories, wars, and creation date.

        Falls back on default guild if no guild is specified.
        """
        await interaction.response.defer()

        data = await get_data(guild, interaction)
        if data == "warn":
            return await interaction.followup.send(embed=ErrorEmbed("Default guild name and tag have not been set. Please get an admin to run `/guild_settings` and set it."))
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching guild data"))

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
    @app_commands.describe(guild="The guild name or prefix of the target guild")
    async def online(self, interaction: discord.Interaction, guild: str = None):
        """
        Show a list or embed of online members in the specified (or default) guild.
        """
        await interaction.response.defer()

        data = await get_data(guild, interaction)
        if data == "warn":
            return await interaction.followup.send(embed=ErrorEmbed("Default guild name and tag have not been set. Please get an admin to run `/guild_settings` and set it."))
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching guild data"))
        embed = await get_online(data, return_embed=True)

        await interaction.followup.send(embed=embed)


    @app_commands.command(name="members", description="View a list of all players in a guild")
    @app_commands.describe(guild="The guild name or prefix of the target guild")
    async def members(self, interaction: discord.Interaction, guild: str = None):
        """
        Display all guild members grouped by rank with their join dates in a paginated embed.
        """
        await interaction.response.defer()

        data = await get_data(guild, interaction)
        if data == "warn":
            return await interaction.followup.send(embed=ErrorEmbed("Default guild name and tag have not been set. Please get an admin to run `/guild_settings` and set it."))
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching guild data"))
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
    @app_commands.describe(guild="The guild name or prefix of the target guild")
    @rate_limit_check()
    async def gxp(self, interaction: discord.Interaction, guild: str = None):
        """
        Show Guild Experience (GXP) contributions by each player, sorted descending.
        """
        await interaction.response.defer()

        data = await get_data(guild, interaction)
        if data == "warn":
            return await interaction.followup.send(embed=ErrorEmbed("Default guild name and tag have not been set. Please get an admin to run `/guild_settings` and set it."))
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching guild data"))
        rows = []

        for rank in data["members"]:
            if rank == "total":
                continue
            for player, player_data in data["members"][rank].items():
                rows.append([player, player_data["contributed"]])

        # Sort by contributed XP descending
        rows = sorted(rows, key=lambda x: x[1], reverse=True)

        # Format XP numbers with commas
        for idx, row in enumerate(rows):
            rows[idx][1] = f"{row[1]:,} "

        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "XP"],
            rows,
            title=f"{data['name']}: GXP Contributions",
            color=discord.Color.blue(),
            rows_per_page=20
        )


    @app_commands.command(name="activity", description="Show last join times for all players in a guild")
    @app_commands.describe(guild="The guild name or prefix of the target guild", order="The order to sort in (descending by default)")
    @app_commands.choices(order=[
        app_commands.Choice(name="Ascending", value="asc"),
        app_commands.Choice(name="Descending", value="desc")
    ])
    @rate_limit_check()
    async def activity(self, interaction: discord.Interaction, guild: str = None, order: app_commands.Choice[str] = "desc"):
        """
        Display last join times of guild members, sorted by inactivity.

        Supports ascending or descending sorting.
        """
        await interaction.response.defer()

        try:
            order = order.value
        except (ValueError, AttributeError):
            pass

        data = await get_data(guild, interaction)
        if data == "warn":
            return await interaction.followup.send(embed=ErrorEmbed("Default guild name and tag have not been set. Please get an admin to run `/guild_settings` and set it."))
        if not data:
            return await interaction.followup.send(embed=ErrorEmbed("Error fetching guild data"))
        members_data = data["members"]

        member_set = set()
        for rank in members_data:
            if isinstance(members_data[rank], dict):
                member_set.update(members_data[rank])

        members_list = list(member_set)
        if not members_list:
            return await interaction.followup.send(embed=ErrorEmbed("Guild has no members."))

        # Fetch last join times from local DB for all guild members
        placeholders = ','.join(['%s'] * len(members_list))
        query = f"SELECT name, lastjoin FROM player_last_join WHERE name IN ({placeholders})"
        res = await Database.fetch(query, members_list)
        last_join_times = {result["name"]: result["lastjoin"] for result in res}

        now = datetime.datetime.utcnow()
        rows = []
        for name in members_list:
            try:
                stamp = last_join_times[name]
            except KeyError:
                continue

            if stamp:
                delta = now - datetime.datetime.utcfromtimestamp(stamp)
                display = f"{delta.days}d {delta.seconds // 3600}h"
            else:
                display = "30d+"
            rows.append((name, display))

        # Sort by longest inactive first (or ascending)
        rows.sort(
            key=lambda r: (r[1] != "30d+", *map(int, (r[1].rstrip("dh").replace("d", " ").split() + ["0"])[:2])),
            reverse=(order == "desc")
        )

        await PaginatedTextTableEmbed.send(
            interaction,
            ["Name", "Last Join"],
            rows,
            title=f"Member Activity of {data['name']}: ({len(rows)})",
            rows_per_page=20
        )



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(GuildCommands(bot))
