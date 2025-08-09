import discord, os

from discord.ext import commands
from discord import app_commands, File

from core.config import config

FFA_MAPS_DIR = "assets/ffa_maps"



def format_label(filename: str) -> str:
    """
    Convert a filename into a human-readable label.

    Removes the file extension, replaces underscores with spaces,
    and converts the string to title case.
    """
    # Split filename to remove extension
    name, _ = os.path.splitext(filename)
    # Replace underscores and capitalize words
    return name.replace("_", " ").title()


class FFAMapSelect(discord.ui.Select):
    """
    Dropdown select menu for choosing an FFA map.

    Displays all map files in the FFA_MAPS_DIR as options.
    Restricts interaction to the command invoker.
    On selection, sends the chosen map image.
    """
    def __init__(self, author: discord.User):
        self.author = author

        # List all map files and create SelectOptions with formatted labels
        files = [f for f in os.listdir(FFA_MAPS_DIR)]
        options = [discord.SelectOption(label=format_label(f), value=f) for f in files]

        super().__init__(
            placeholder="Select an FFA map to view...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """
        Handle interaction when a map is selected from the dropdown.

        Validates user authorization, checks file existence,
        and edits the original message to show the selected map image.
        """
        # Only allow the command invoker to interact with this menu
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(
                "Only the command user can use this menu.", ephemeral=True
            )

        selected_file = self.values[0]
        file_path = os.path.join(FFA_MAPS_DIR, selected_file)

        # Check if selected map file exists
        if not os.path.isfile(file_path):
            return await interaction.response.send_message("Map not found.", ephemeral=True)

        label = format_label(selected_file)
        # Open the map file in binary mode to send as attachment
        with open(file_path, "rb") as f:
            file = File(f, filename=selected_file)

        embed = discord.Embed(
            title=f"{label} FFA Map",
            color=discord.Color.blue()
        )
        # Set embed image to the attached file
        embed.set_image(url=f"attachment://{selected_file}")

        # Edit original message with the new embed and attachment, keep the dropdown visible
        await interaction.response.edit_message(
            embed=embed,
            attachments=[file],
            view=self.view
        )



class FFAMapView(discord.ui.View):
    """
    Discord UI View containing the FFA map dropdown menu.

    Automatically times out after 60 seconds.
    """
    def __init__(self, author: discord.User):
        super().__init__(timeout=60)
        # Add the dropdown select to the view
        self.add_item(FFAMapSelect(author))



class FFA(commands.Cog):
    """
    Cog providing the /ffa command to browse and view FFA maps.
    """
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="ffa", description="Browse and view FFA maps.")
    async def ffa(self, interaction: discord.Interaction):
        """
        Command handler for /ffa.

        Sends an embed with a dropdown menu allowing users to select and
        display maps from the assets/ffa_maps directory.
        """
        # Create initial embed prompting user to select a map
        embed = discord.Embed(
            title="Select a map",
            description="Use the dropdown below to view an FFA map",
            color=discord.Color.blue()
        )
        # Create a view containing the dropdown menu
        view = FFAMapView(interaction.user)
        # Send the initial message with embed and interactive dropdown
        await interaction.response.send_message(embed=embed, view=view)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = FFA(bot)
    await bot.add_cog(cog)

    # Remove existing global command to avoid duplicates
    existing_global = bot.tree.get_command("ffa")
    if existing_global:
        bot.tree.remove_command("ffa")

    # Manually register the command only for guilds that receive ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.ffa, guild=guild)
