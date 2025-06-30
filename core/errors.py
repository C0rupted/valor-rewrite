from discord.ext import commands

async def handle_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore for now
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to run this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing arguments for this command.")
    else:
        await ctx.send("An unexpected error occurred.")
        raise error

async def setup(bot: commands.Bot):
    @bot.event
    async def on_command_error(ctx, error):
        await handle_command_error(ctx, error)
