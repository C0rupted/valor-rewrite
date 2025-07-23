import discord, logging

from discord import app_commands
from discord.ext import commands

from database.connection import Database
from util.board import BoardView, build_board
from util.embeds import ErrorEmbed, TextTableEmbed
from util.guilds import guild_names_from_tags
from util.ranges import get_range_from_string



class GRaids(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="graids", description="Leaderboard for guild raid counts")
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Range of days in the past you want to check",
        players="Filter by player names (comma-separated)",
        guild_wise="Show raid totals per guild instead of individual players"
    )
    async def graids(self, interaction: discord.Interaction, guilds: str = None, range: str = "7", players: str = None, guild_wise: bool = False):
        if guild_wise and (players or guilds):
            return await interaction.response.send_message(
                embed=ErrorEmbed("You cannot use `guild_wise` together with `players` or `guilds`."),
                ephemeral=True
            )

        range = await get_range_from_string(range)

        if not range:
            return await interaction.response.send_message(embed=ErrorEmbed("Invalid range input"), ephemeral=True)
        
        prepared_params = [range[0], range[1]]

        template_query_params = {
            "TIME_CLAUSE": "A.`time` > %s AND A.`time` <= %s",
            "GUILD_CLAUSE": "",
            "UUIDS": ""
        }

        uuidtoname = {}

        if players:
            names = [n.strip() for n in players.split(",") if n.strip()]
            res = await Database.fetch(
                "SELECT uuid, name FROM uuid_name WHERE name IN (" + ",".join(["%s"] * len(names)) + ")",
                names
            )

            if not res:
                return await interaction.response.send_message(embed=ErrorEmbed(f"No UUIDs found for: {players}"), ephemeral=True)

            uuidtoname = {}
            uuids = []

            for entry in res:
                uuidtoname[entry["uuid"]] = entry["name"]
                uuids.append(entry["uuid"])

            if not uuids:
                return await interaction.response.send_message(embed=ErrorEmbed("No valid UUIDs provided."), ephemeral=True)

            template_query = '''
SELECT ROW_NUMBER() OVER(ORDER BY raid_cnt DESC) AS `raid_cnt`, name, guild, raid_cnt
FROM (
    SELECT B.name, A.guild, SUM(A.num_raids) AS raid_cnt
    FROM guild_raid_records A
    LEFT JOIN uuid_name B ON A.uuid = B.uuid
    WHERE {TIME_CLAUSE} AND A.uuid IN ({UUIDS})
    GROUP BY A.uuid, A.guild
    ORDER BY raid_cnt DESC
) C LIMIT 50;
'''
            template_query_params["UUIDS"] = ",".join(["%s"] * len(uuids))
            prepared_params.extend(uuids)

        elif not guild_wise:
            template_query = '''
SELECT ROW_NUMBER() OVER(ORDER BY raid_cnt DESC) AS `rank`, name, raid_cnt
FROM (
    SELECT B.name, SUM(A.num_raids) AS raid_cnt
    FROM guild_raid_records A
    LEFT JOIN uuid_name B ON A.uuid = B.uuid
    WHERE {TIME_CLAUSE} {GUILD_CLAUSE}
    GROUP BY A.uuid
    ORDER BY raid_cnt DESC
) C LIMIT 50;
'''
        else:
            template_query = '''
SELECT ROW_NUMBER() OVER(ORDER BY raid_cnt DESC) AS `rank`, guild, raid_cnt
FROM (
    SELECT guild, SUM(num_raids) AS raid_cnt
    FROM guild_raid_records A
    WHERE {TIME_CLAUSE} {GUILD_CLAUSE}
    GROUP BY guild
    ORDER BY raid_cnt DESC
) C LIMIT 50;
'''

        if guilds:
            tags = [tag.strip() for tag in guilds.split(",") if tag.strip()]
            tags, _ = await guild_names_from_tags(tags)
            template_query_params["GUILD_CLAUSE"] = "AND A.guild IN (" + ",".join(["%s"] * len(tags)) + ")"
            prepared_params.extend(tags)

        await interaction.response.defer()

        query = template_query.format(**template_query_params)
        result = await Database.fetch(query, prepared_params)

        if not result:
            return await interaction.followup.send(embed=ErrorEmbed("No results for the specified parameters."), ephemeral=True)


        rows = [[
            row["guild" if guild_wise else "name"],
            str(row["raid_cnt"])
        ] for row in result]


        view = BoardView(interaction.user.id, rows, title=f"Raids", stat_counter="Raids", is_guild_board=(True if guild_wise else False))

        if view.is_fancy:
            board = await build_board(view.data, view.page, is_guild_board=(True if guild_wise else False))
            await interaction.followup.send(embed=None, view=view, file=board)
        else:
            start = view.page * 10
            end = start + 10
            sliced = view.data[start:end]

            for i in range(len(sliced)):
                sliced[i] = [f"{i+start+1}.", sliced[i][0], sliced[i][1]]

            embed = TextTableEmbed([" Rank ", " Name", " Raids "], sliced, title=view.title, color=0x333333)
            await interaction.followup.send(embed=embed, view=view, file=None)

async def setup(bot: commands.Bot):
    await bot.add_cog(GRaids(bot))