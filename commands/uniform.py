import discord, ast, base64
from discord import app_commands, File
from discord.ext import commands
from PIL import Image

from core.config import config
from util.embeds import ErrorEmbed
from util.roles import is_ANO_member
from util.requests import request


class Uniform(commands.Cog):
    """
    Cog providing the /uniform command to generate a Minecraft skin with ANO uniform overlay.
    """
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="uniform",
        description="Generates skin with ANO uniform based on the provided username."
    )
    @app_commands.choices(
        skin_variant=[
            app_commands.Choice(name="Male", value="male"),
            app_commands.Choice(name="Female", value="female")
        ]
    )
    async def uniform(self, interaction: discord.Interaction, username: str, skin_variant: app_commands.Choice[str]):
        """
        Slash command to generate a Minecraft skin with an ANO uniform overlay.

        Args:
            interaction (discord.Interaction): The interaction object from Discord.
            username (str): Minecraft username whose skin will be used.
            skin_variant (Choice[str]): The uniform variant, either 'male' or 'female'.

        Workflow:
        - Verifies user is an ANO member (except if in testing mode).
        - Fetches the player's UUID and skin data from Mojang APIs.
        - Converts legacy 32-pixel skins to 64-pixel format.
        - Applies a transparent uniform overlay PNG (male/female).
        - Sends the final composited skin image back as a file attachment.
        """
        # Check if the user has permission to use this command (ANO member or testing mode)
        if not is_ANO_member(interaction.user) and not config.TESTING:
            await interaction.response.send_message(
                embed=ErrorEmbed("Only ANO members can wear this uniform!"),
                ephemeral=True
            )
            return

        # Acknowledge command and defer response as skin fetching & processing takes time
        await interaction.response.defer()

        # Fetch UUID for the given username from Mojang API
        uuid = (await request(f"https://api.mojang.com/users/profiles/minecraft/{username}")).get("id", "")
        if not uuid:
            return await interaction.followup.send(embed=ErrorEmbed("Player not found."))

        # Fetch skin data JSON, decode the base64 texture property, and parse it
        data = await request(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}")
        skindata = ast.literal_eval(base64.b64decode(data["properties"][0]["value"]).decode("UTF-8"))

        # Download player skin image as a PIL image from the skin URL
        player_skin = Image.open(await request(skindata["textures"]["SKIN"]["url"], return_type="stream"))

        # Handle legacy 32-pixel tall skins by converting them to 64-pixel tall format
        if player_skin.height == 32:
            # Extract body parts
            leg = player_skin.crop((0, 16, 16, 32))
            arm = player_skin.crop((40, 16, 56, 32))
            body = player_skin.crop((16, 16, 40, 32))
            head = player_skin.crop((0, 0, 64, 16))

            # Create a new transparent 64x64 canvas for the updated skin
            player_skin = Image.new("RGBA", (64, 64), (0, 0, 0, 0))

            # Paste extracted body parts in new 64x64 layout positions
            player_skin.paste(leg, (16, 48))
            player_skin.paste(leg, (0, 16))
            player_skin.paste(arm, (40, 16))
            player_skin.paste(arm, (32, 48))
            player_skin.paste(body, (16, 16))
            player_skin.paste(head, (0, 0))

        # Clear specific rectangular areas on the skin by pasting transparent rectangles,
        # likely to remove legacy overlay artifacts before applying uniform overlay
        rect1 = Image.new("RGBA", (64, 16), (0, 0, 0, 0))
        rect2 = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

        player_skin.paste(rect1, (0, 32))
        player_skin.paste(rect2, (0, 48))
        player_skin.paste(rect2, (48, 48))

        # Load the appropriate uniform overlay PNG image for the selected variant
        if skin_variant.value == "male":
            uniform_skin = Image.open("assets/male_uniform_overlay.png").convert("RGBA")
        elif skin_variant.value == "female":
            uniform_skin = Image.open("assets/female_uniform_overlay.png").convert("RGBA")
        else:
            # Defensive fallback if somehow an invalid variant is provided
            await interaction.followup.send(embed=ErrorEmbed("Invalid skin variant"), ephemeral=True)
            return

        # Combine the player's skin with the uniform overlay, preserving transparency
        final_skin = Image.alpha_composite(player_skin, uniform_skin)

        # Save the composited image temporarily to disk
        final_skin.save("/tmp/uniform_skin.png")

        # Create a Discord file object for sending the image
        file = File("/tmp/uniform_skin.png", filename="uniform_skin.png")

        # Send the final image as a follow-up message attachment
        await interaction.followup.send(file=file)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    cog = Uniform(bot)
    await bot.add_cog(cog)

    # Remove any existing global /uniform command to avoid conflicts
    existing_global = bot.tree.get_command("uniform")
    if existing_global:
        bot.tree.remove_command("uniform")

    # Register /uniform only in the guilds configured for ANO commands
    for guild_id in config.ANO_COMMANDS_GUILD_IDS:
        guild = discord.Object(id=int(guild_id))
        bot.tree.add_command(cog.uniform, guild=guild)
