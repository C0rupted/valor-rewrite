import discord, logging, traceback

from core.antispam import RateLimitExceeded
from discord.ext import commands
from util.embeds import ErrorEmbed



async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """
    Bot-wide global error handler for application commands.

    Args:
        interaction (discord.Interaction): The interaction that caused the error.
        error (discord.app_commands.AppCommandError): The error raised during command execution.
    """
    # Handle known RateLimitExceeded errors with a user-friendly message
    if isinstance(error, RateLimitExceeded):
        embed = ErrorEmbed(error.message)
    else:
        # Log full traceback of unexpected errors for debugging
        logging.error(f"An error occurred while executing a {error.command} command:")
        logging.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))

        # Prepare a generic error message to show to users
        embed = ErrorEmbed(
            "An unexpected error occurred while executing the command.",
            footer="Please contact ANO and report this bug"
        )

    # Send the error embed as a followup if the original response was already sent
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        # Otherwise send the response message with the error embed, ephemeral for privacy
        await interaction.response.send_message(embed=embed, ephemeral=True)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    # Assign the on_app_command_error coroutine as the global error handler for app commands
    bot.tree.error(coro=on_app_command_error)
