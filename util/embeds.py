import discord

def ErrorEmbed(description="An error occurred."):
    return discord.Embed(description=description, color=discord.Color.red())