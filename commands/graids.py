import discord

from discord import app_commands
from discord.ext import commands

from core.antispam import rate_limit_check
from database import Database
from util.board import BoardView, build_board
from util.embeds import ErrorEmbed, TextTableEmbed
from util.guilds import guild_names_from_tags
from util.ranges import get_range_from_string, range_alt



class GRaids(commands.Cog):
    """
    Cog providing the /graids command to display guild raid leaderboards.

    Supports filtering by guilds, players, date ranges, and guild-wise aggregation.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(name="graids", description="Leaderboard for guild raid counts")
    @app_commands.describe(
        guilds="Filter by guild tags (comma-separated)",
        range="Number of days ago, or a range like '0,7', or season name like 'season26'",
        players="Filter by player usernames (comma-separated)",
        guild_wise="Show raid totals per guild instead of individual players"
    )
    @rate_limit_check()
    async def graids(
        self,
        interaction: discord.Interaction,
        guilds: str = None,
        range: str = "7",
        players: str = None,
        guild_wise: bool = False
    ):
        """
        Show leaderboard of raid counts filtered by players, guilds, and date range.

        Workflow:
        1. Validate mutually exclusive options (guild_wise cannot combine with players/guilds).
        2. Parse the input range into timestamps.
        3. Build SQL query dynamically depending on filters.
        4. Fetch and process the results from the database.
        5. Display results using BoardView with pagination or fallback to a simple embed.
        """
        await interaction.response.defer()
        # A guild-wise board cannot be combined with players or guild filters
        if guild_wise and (players or guilds):
            return await interaction.followup.send(embed=ErrorEmbed("You cannot use `guild_wise` together with `players` or `guilds`."))
        # Players and guilds filters cannot be used together
        if guilds and players:
            return await interaction.followup.send(embed=ErrorEmbed("You cannot use `players` and `guilds` together."))

        # Convert the range input to start/end timestamps; no max limit
        range = await get_range_from_string(range, max_allowed_range=None)

        if not range:
            return await interaction.followup.send(embed=ErrorEmbed("Invalid range input"))

        prepared_params = [range[0], range[1]]

        # Initialize query template placeholders
        template_query_params = {
            "TIME_CLAUSE": "A.`time` > %s AND A.`time` <= %s",
            "GUILD_CLAUSE": "",
            "UUIDS": ""
        }

        uuidtoname = {}

        if players:
            # Parse player names and get their UUIDs
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

            # SQL to show player-wise raid counts filtered by UUIDs
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
            # SQL for player-wise leaderboard without filters on UUIDs
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
            # SQL for guild-wise leaderboard aggregation
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
            # Parse guild tags and resolve to official names
            tags = [tag.strip() for tag in guilds.split(",") if tag.strip()]
            tags, _ = await guild_names_from_tags(tags)
            template_query_params["GUILD_CLAUSE"] = "AND A.guild IN (" + ",".join(["%s"] * len(tags)) + ")"
            prepared_params.extend(tags)

        # Fill in the template SQL with dynamic WHERE clauses
        query = template_query.format(**template_query_params)
        # Execute query with all parameters
        result = await Database.fetch(query, prepared_params)

        if not result:
            return await interaction.followup.send(embed=ErrorEmbed("No results for the specified parameters."), ephemeral=True)

        # Prepare rows for the leaderboard display: [Name/Guild, Raid Count]
        rows = [[
            row["guild" if guild_wise else "name"],
            str(row["raid_cnt"])
        ] for row in result]

        # Create a BoardView for interactive paging
        view = BoardView(
            interaction.user.id,
            rows,
            title="Raids",
            stat_counter="Raids",
            is_guild_board=guild_wise
        )

        if view.is_fancy:
            # If user prefers fancy board, send as an image file with the interactive view
            board = await build_board(view.data, view.page, is_guild_board=guild_wise)
            await interaction.followup.send(view=view, file=board)
        else:
            # Otherwise send as a simple embed with text table and navigation buttons
            start = view.page * 10
            end = start + 10
            sliced = view.data[start:end]

            for i in range_alt(len(sliced)):
                sliced[i] = [f"{i+start+1}.", sliced[i][0], sliced[i][1]]

            embed = TextTableEmbed(
                ["Rank", "Name", "Raids"],
                sliced,
                title=view.title,
                color=0x333333
            )
            await interaction.followup.send(embed=embed, view=view)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(GRaids(bot))
