import discord, time, json, os, re
from discord import app_commands, Interaction, ButtonStyle, Message
from discord.ext import commands
from discord.ui import View, Button

from core.config import config
from util.embeds import ErrorEmbed
from util.roles import is_ANO_high_rank


# File used to store the last reported Annihilation timestamp
ANNI_FILE = "storages/annihilation_tracker.json"
# Embed color for Annihilation-related messages
ANNI_EMBED_COLOR = 0x7A1507


class AnnihilationTracker(commands.Cog):
    """
    Cog containing commands for tracking and reporting Annihilation events.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    def load_annihilation(self):
        """
        Load the Annihilation tracker file from disk.

        Returns:
            dict: Dictionary containing the last saved timestamp,
                  or an empty dict if file is missing/invalid.
        """
        if not os.path.exists(ANNI_FILE):
            return {}
        try:
            with open(ANNI_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Something wrong with the file — return empty data
            return {}


    def save_annihilation(self, timestamp: int):
        """
        Save a new Annihilation timestamp to disk.

        Args:
            timestamp (int): Unix timestamp for the next Annihilation event.
        """
        with open(ANNI_FILE, "w") as f:
            json.dump({"timestamp": timestamp}, f)


    @app_commands.command(name="annihilation", description="Check the next reported Annihilation World Event time.")
    async def annihilation(self, interaction: discord.Interaction):
        """
        Command to display the next scheduled Annihilation event time.

        If no valid timestamp is stored, shows that no Annihilation is reported, and the most recent Annihilation time.
        """
        data = self.load_annihilation()
        now = int(time.time())
        timestamp = data.get("timestamp", 0)

        # If there is no record or the saved time is already in the past
        if not data or data.get("timestamp", 0) < now:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Annihilation Tracker",
                    description=(
                        f"There is currently no Annihilation reported.\n\n"
                        f"Most recent Annie was at <t:{timestamp}:f> (<t:{timestamp}:R>)"
                    ),
                    color=ANNI_EMBED_COLOR
                ).set_footer(text=f"Did Annie wake up? Ask an ANO high rank to report it!")
            )

        # Otherwise, show the next scheduled Annihilation
        return await interaction.response.send_message(
            embed=discord.Embed(
                title="Annihilation Tracker",
                description=f"Next Annihilation is at <t:{timestamp}:f> (<t:{timestamp}:R>)",
                color=ANNI_EMBED_COLOR
            ).set_footer(text=f"Is that time inaccurate? Report it to an ANO high rank!")
        )


    @app_commands.command(
        name="report_annihilation",
        description="Report or update the time of the next Annihilation event."
    )
    @app_commands.describe(
        time_until="Time until next Annihilation (e.g. '2h30m', '1h 45m') or 'none'"
    )
    async def report_annihilation(self, interaction: discord.Interaction, time_until: str):
        """
        Command to report or update the Annihilation time.

        Workflow:
        1. Permission check — only ANO high rank (or TESTING mode) can report.
        2. Handle 'none' input to clear stored data.
        3. Parse time formats like '2h30m', '1h', '45m'.
        4. If an existing future timestamp exists, ask for confirmation.
        5. Save the new timestamp and confirm to the user.
        """
        await interaction.response.defer()

        # Permission check
        if not is_ANO_high_rank(interaction.user) and not config.TESTING:
            return await interaction.followup.send(
                embed=ErrorEmbed("You do not have permission to report an Annihilation time."),
                ephemeral=True
            )

        # Special case: remove the recorded time
        if time_until.lower() == "none":
            self.save_annihilation(0)
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Annihilation Time Deleted",
                    description="Annihilation time has been deleted.",
                    color=ANNI_EMBED_COLOR
                )
            )

        # Parse provided time string into hours and minutes
        match = re.match(
            r"(?:(\d+)h)?\s*(?:(\d+)m)?",
            time_until.replace(" ", ""),
            re.IGNORECASE
        )
        if not match:
            return await interaction.followup.send(
                embed=ErrorEmbed("Invalid format. Use `2h30m`, `1h 45m`, `1h`, or `30m`"),
                ephemeral=True
            )

        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0

        # Reject zero-length durations
        if hours == 0 and minutes == 0:
            return await interaction.followup.send(
                embed=ErrorEmbed("Duration must be greater than zero."),
                ephemeral=True
            )

        # Compute the new event timestamp
        new_ts = int(time.time()) + (hours * 3600) + (minutes * 60)
        existing = self.load_annihilation()

        # If an Annihilation is already scheduled in the future, require confirmation
        if existing and existing["timestamp"] > int(time.time()):
            old_ts = existing["timestamp"]
            embed = discord.Embed(
                title="Annihilation Already Reported",
                description=(
                    f"Annihilation is already set for <t:{old_ts}:f> (<t:{old_ts}:R>). "
                    f"React with ✅ within 30s to overwrite with `{time_until}`."
                ),
                color=ANNI_EMBED_COLOR
            )

            return await interaction.followup.send(
                embed=embed,
                view=ReportAnnihilationView(interaction.user, new_ts, self.save_annihilation)
            )

        # Save the new report directly if no active one exists
        self.save_annihilation(new_ts)
        await interaction.followup.send(
            embed=discord.Embed(
                title="Annihilation Time Reported",
                description=f"Next Annihilation is set for <t:{new_ts}:f> (<t:{new_ts}:R>)",
                color=ANNI_EMBED_COLOR
            )
        )



class ReportAnnihilationView(View):
    """
    Interactive confirmation view for overwriting an existing Annihilation time.
    """

    def __init__(self, author: discord.User, new_timestamp: int, func, timeout: float = 30.0):
        """
        Args:
            author (discord.User): The user who initiated the overwrite request.
            new_timestamp (int): The proposed new Annihilation time.
            timeout (float): How long (in seconds) the confirmation stays active.
        """
        super().__init__(timeout=timeout)
        self.author = author
        self.new_timestamp = new_timestamp
        self.function = func
        self.confirmed = False
        self.message: Message = None


    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Only allow the original author to interact with this confirmation view.
        """
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Only the user who initiated this command can confirm it.",
                ephemeral=True
            )
            return False
        return True


    @discord.ui.button(label="Confirm", style=ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: Button):
        """
        Callback for confirm button
        """
        self.confirmed = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Annihilation Time Overwritten",
                description=(
                    f"Annihilation time has been updated to <t:{self.new_timestamp}:f> "
                    f"(<t:{self.new_timestamp}:R>)"
                ),
                color=ANNI_EMBED_COLOR
            ),
            view=None
        )
        self.function(self.new_timestamp)
        self.stop()



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = AnnihilationTracker(bot)
    await bot.add_cog(cog)

    # Remove existing global command to avoid duplicates
    existing_global = bot.tree.get_command("report_annihilation")
    if existing_global:
        bot.tree.remove_command("report_annihilation")

    # Register the command for each ANO guild
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.report_annihilation, guild=guild)
