import discord, time, json, os, re
from discord import app_commands, Interaction, ButtonStyle, Message
from discord.ext import commands
from discord.ui import View, Button

from core.config import config
from util.embeds import ErrorEmbed
from util.roles import is_ANO_high_rank


ANNI_FILE = "storages/annihilation_tracker.json"
ANNI_EMBED_COLOR = 0x7A1507


class AnnihilationTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def load_annihilation(self):
        if not os.path.exists(ANNI_FILE):
            return None
        try:
            with open(ANNI_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def save_annihilation(self, timestamp: int):
        with open(ANNI_FILE, "w") as f:
            json.dump({"timestamp": timestamp}, f)

    @app_commands.command(name="annihilation", description="Check the next Annihilation time.")
    async def annihilation(self, interaction: discord.Interaction):
        data = self.load_annihilation()
        now = int(time.time())
        if not data or data.get("timestamp", 0) < now:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Annihilation Tracker",
                    description="There is currently no Annihilation reported.",
                    color=ANNI_EMBED_COLOR
                )
            )

        timestamp = data["timestamp"]
        return await interaction.response.send_message(
            embed=discord.Embed(
                title="Annihilation Tracker",
                description=f"Next Annihilation is at <t:{timestamp}:f> (<t:{timestamp}:R>)",
                color=ANNI_EMBED_COLOR
            )
        )

    @app_commands.command(name="report_annihilation", description="Report or update the time of the next Annihilation event.")
    @app_commands.describe(time_until="Time until next Annihilation (e.g. '2h30m', '1h 45m') or 'none'")
    @app_commands.guild_only()
    async def report_annihilation(self, interaction: discord.Interaction, time_until: str):
        if not is_ANO_high_rank(interaction.user) and not config.TESTING:
            return await interaction.response.send_message(embed=ErrorEmbed("You do not have permission to report an Annihilation time."), ephemeral=True)

        if time_until.lower() == "none":
            self.save_annihilation(0)
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Annihilation Time Deleted",
                    description="Annihilation time has been deleted.",
                    color=ANNI_EMBED_COLOR
                )
            )

        match = re.match(r"(?:(\d+)h)?\s*(?:(\d+)m)?", time_until.replace(" ", ""), re.IGNORECASE)
        if not match:
            return await interaction.response.send_message(embed=ErrorEmbed("Invalid format. Use `2h30m`, `1h 45m`, `1h`, or `30m`"), ephemeral=True)

        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        if hours == 0 and minutes == 0:
            return await interaction.response.send_message(embed=ErrorEmbed("Duration must be greater than zero."), ephemeral=True)

        new_ts = int(time.time()) + (hours * 3600) + (minutes * 60)
        existing = self.load_annihilation()

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
            await interaction.response.send_message(embed=embed, view=ReportAnnihilationView(interaction.user, new_ts))

        self.save_annihilation(new_ts)
        return await interaction.response.send_message(
            embed=discord.Embed(
                title="Annihilation Time Reported",
                description=f"Next Annihilation is set for <t:{new_ts}:f> (<t:{new_ts}:R>)",
                color=ANNI_EMBED_COLOR
            )
        )
    
class ReportAnnihilationView(View):
    def __init__(self, author: discord.User, new_timestamp: int, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author = author
        self.new_timestamp = new_timestamp
        self.confirmed = False
        self.message: Message = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Only the user who initiated this command can confirm it.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: Button):
        self.confirmed = True
        await interaction.response.edit_message(
            embed = discord.Embed(
                title = "Annihilation Time Overwritten",
                description = (
                    f"Annihilation time has been updated to <t:{self.new_timestamp}:f> "
                    f"(<t:{self.new_timestamp}:R>)"
                ),
                color = ANNI_EMBED_COLOR
            ),
            view = None
        )
        self.stop()

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

async def setup(bot):
    cog = AnnihilationTracker(bot)
    await bot.add_cog(cog)

    existing_global = bot.tree.get_command("report_annihilation")
    if existing_global:
        bot.tree.remove_command("report_annihilation")

    # Manually register the command only for guilds that receive ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.report_annihilation, guild=guild)