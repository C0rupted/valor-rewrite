import discord

from discord.ext import commands
from discord import app_commands, Interaction

from core.config import config
from util.embeds import ErrorEmbed
from util.roles import is_ANO_military_member


# Define available role pings with their metadata: display name, description, emoji, and role ID.
PING_ROLES = {
    "ffa": {
        "name": "FFA",
        "description": "FFA run",
        "emoji": "⚔️",
        "role_id": 892884695199666187
    },
    "dps": {
        "name": "DPS",
        "description": "DPS players needed",
        "emoji": "💥",
        "role_id": 892885182300954624
    },
    "guardian": {
        "name": "Guardian",
        "description": "Guardian needed",
        "emoji": "🛡️",
        "role_id": 892884953996591164
    },
    "healer": {
        "name": "Healer",
        "description": "Healer needed",
        "emoji": "❤️",
        "role_id": 892885381744320532
    },
    "trg": {
        "name": "Royal Guard",
        "description": "Royal Guard Ping",
        "emoji": "👑",
        "role_id": 683785435117256939
    },
}



class PingsButton(discord.ui.Button):
    """
    Button representing a single role ping.
    Only the user who invoked the command can press the buttons.
    """

    def __init__(self, ping_id: str, author_id: int):
        """
        Initialize button with emoji and store ping ID and author ID for permission checks.
        """
        self.ping_id = ping_id
        self.author_id = author_id
        data = PING_ROLES[ping_id]
        super().__init__(emoji=data["emoji"], style=discord.ButtonStyle.secondary)


    async def callback(self, interaction: Interaction):
        """
        Callback triggered when the button is clicked.

        - Checks if interaction user is the command author.
        - Checks if user has appropriate military permissions or is in testing mode.
        - Sends a ping for the corresponding role if permitted.
        """
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "Only the user who used the command can interact with these buttons.",
                ephemeral=True
            )

        if not is_ANO_military_member(interaction.user) and not config.TESTING:
            return await interaction.response.send_message(
                embed=ErrorEmbed("No Permissions"), ephemeral=True
            )

        data = PING_ROLES[self.ping_id]
        # Send a non-ephemeral message pinging the role
        await interaction.response.send_message(f"<@&{data['role_id']}>", ephemeral=False)



class PingsButtonView(discord.ui.View):
    """
    View container holding all ping buttons.
    The buttons expire after 30 seconds.
    """

    def __init__(self, author: discord.User):
        super().__init__(timeout=30)
        # Add a button for each ping role defined
        for key in PING_ROLES:
            self.add_item(PingsButton(key, author.id))



class Pings(commands.Cog):
    """
    Cog containing the /pings slash command and button interaction logic.
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pings", description="Send a role ping using buttons.")
    async def pings(self, interaction: Interaction):
        """
        /pings command handler.

        - Permission check for ANO military members or testing mode.
        - Sends an embed describing available role pings with interactive buttons.
        """
        if not is_ANO_military_member(interaction.user) and not config.TESTING:
            return await interaction.response.send_message(
                embed=ErrorEmbed("No Permissions"),
                ephemeral=True
            )

        embed = discord.Embed(
            title="Available Role Pings:",
            description=(
                "\n".join(
                    f"{data['emoji']} **|     {data['name']}** — {data['description']}"
                    for data in PING_ROLES.values()
                ) + "\n\n**Click a button to ping the role:**"
            ),
            color=0x00FFFF
        )

        view = PingsButtonView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = Pings(bot)
    await bot.add_cog(cog)

    # Remove any existing global registration to avoid conflicts
    existing_global = bot.tree.get_command("pings")
    if existing_global:
        bot.tree.remove_command("pings")

    # Register /pings command only in guilds configured for ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.pings, guild=guild)
