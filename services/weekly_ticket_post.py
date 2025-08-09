import logging, asyncio, datetime

from discord.ext import commands, tasks

from core.config import config
from util.embeds import PaginatedTextTableEmbed


# Constants for when to post tickets weekly
TARGET_WEEKDAY = 6  # Sunday (0 = Monday, 6 = Sunday)
TARGET_HOUR = 17    # 5 PM
TARGET_MINUTE = 0   # 00 minutes



class WeeklyTicketPostService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Start the repeating weekly task
        self.ticket_post_loop.start()


    def cog_unload(self):
        # Cancel the task when the cog is unloaded (bot shutdown/reload)
        self.ticket_post_loop.cancel()


    @tasks.loop(hours=168)  # Repeat every 168 hours (1 week)
    async def ticket_post_loop(self):
        from commands.tickets import get_tickets  # Import here to avoid circular imports

        # Get the configured channel to post the tickets leaderboard
        channel = self.bot.get_channel(config.TITAN_CHAT_CHANNEL_ID)
        if channel is None:
            return logging.error("WeeklyTicketPostService: Channel not found for posting tickets.")

        # Fetch ticket leaderboard data
        rows = await get_tickets()

        # If no data found, notify the channel and return
        if not rows:
            await channel.send("No ticket data found this week.")
            return

        headers = ["", "Name", "War", "GXP", "Raid", "Bonus", "Total"]

        # Create the paginated embed view with leaderboard data
        view = PaginatedTextTableEmbed(
            headers,
            rows,
            title="Titans Valor Ticket Leaderboard",
            rows_per_page=20,
            timeout=3600
        )
        embed = view.format_page(0)  # Format first page

        # Send embed with pagination controls
        view.message = await channel.send(embed=embed, view=view)


    @ticket_post_loop.before_loop
    async def before_ticket_post_loop(self):
        # Wait for the bot to be fully ready before starting the loop
        await self.bot.wait_until_ready()

        # Calculate how long to wait until the next scheduled posting time
        now = datetime.datetime.now(datetime.timezone.utc).astimezone()
        target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)

        # Calculate days until the target weekday
        days_ahead = (TARGET_WEEKDAY - now.weekday()) % 7
        # If today is the target weekday but time has passed, schedule for next week
        if days_ahead == 0 and now >= target:
            days_ahead = 7

        target += datetime.timedelta(days=days_ahead)
        wait_seconds = (target - now).total_seconds()

        logging.info(f"Ticket Post Service - Waiting {wait_seconds / 60:.2f} minutes until next scheduled run.")
        await asyncio.sleep(wait_seconds)  # Sleep until the scheduled time



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyTicketPostService(bot))
