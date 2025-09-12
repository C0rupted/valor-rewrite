import discord, time

from discord.ext import commands
from discord import app_commands

from core.config import config
from database import Database
from util.embeds import ErrorEmbed, InfoEmbed
from util.roles import is_ANO_chief
from util.uuid import get_uuid_from_name


class Admin(commands.GroupCog, name="admin"):
    """
    Group cog containing administrative commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="give_ticket_bonuses",
        description="Manually add ticket bonuses to a player."
    )
    @app_commands.describe(
        username="Player username to receive the bonus",
        value="Bonus ticket amount to assign"
    )
    async def give_ticket_bonuses(
        self,
        interaction: discord.Interaction,
        username: str,
        value: int
    ):
        """
        Slash command to manually add ticket bonuses to a given player.

        Workflow:
        1. Permission check — only ANO chiefs (or in testing mode) can run this.
        2. Look up the player's UUID from their username.
        3. Insert a new bonus record into the `ticket_bonuses` database table.
        4. Send a confirmation embed back to the user.

        Args:
            interaction (discord.Interaction): The interaction context.
            username (str): Minecraft username of the target player.
            value (int): Number of bonus tickets to add.
        """

        # Permission check — only ANO chiefs can use this command
        if not is_ANO_chief(interaction.user):
            return await interaction.response.send_message(
                embed=ErrorEmbed("You do not have permission to use this command."),
                ephemeral=True  # Only visible to the command user
            )

        # Defer the interaction to allow time for DB lookups
        await interaction.response.defer()

        # Convert the provided username into a UUID
        uuid = await get_uuid_from_name(username)
        if not uuid:
            return await interaction.followup.send(
                embed=ErrorEmbed("Could not find UUID for this username.")
            )

        # Store the bonus in the database with the current timestamp
        await Database.fetch(
            "INSERT INTO ticket_bonuses (uuid, ticket_bonus, timestamp) VALUES (%s, %s, %s)",
            (uuid, value, str(time.time()))
        )

        # Send a confirmation embed back to the user
        embed = InfoEmbed(
            title="Ticket Bonus Added",
            description=f"Successfully added **{value}** tickets to **{username}** (`{uuid}`)."
        )
        await interaction.followup.send(embed=embed)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = Admin(bot)
    await bot.add_cog(cog)

    # Remove existing global command to avoid duplicates
    existing_global = bot.tree.get_command("admin")
    if existing_global:
        bot.tree.remove_command("admin")

    # Register the command for each ANO guild
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.give_ticket_bonuses, guild=guild)
