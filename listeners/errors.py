import discord, logging, traceback

from discord.ext import commands
from util.embeds import ErrorEmbed


async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    # Log full traceback
    logging.error(f"An error occurred while executing a {error.command} command:")
    logging.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))

    # Send error message to user
    embed = ErrorEmbed("An unexpected error occurred while executing the command.", footer="Please contact ANO and report this bug")
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)



async def setup(bot: commands.Bot):
    bot.tree.error(coro=on_app_command_error)
