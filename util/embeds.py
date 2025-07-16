import discord

def ErrorEmbed(description="An error occurred."):
    return discord.Embed(title="Error!", description=description, color=discord.Color.red())