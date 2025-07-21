import discord, logging
from PIL import Image, ImageDraw, ImageFont

from core.settings import SettingsManager
from util.embeds import TextTableEmbed
from util.mappings import UI_EMOJI_MAP
from util.requests import fetch_player_busts

# Example font path; make sure to replace with your actual font file
FONT_PATH = "assets/fonts/MinecraftRegular.ttf"

class BoardView(discord.ui.View):
    def __init__(self, user_id, data: list[tuple[str, int]], title: str = "Leaderboard", max_page: int = 9999999, stat_counter: str = "Value"):
        super().__init__()
        self.user_id = user_id
        self.data = data
        self.max_page = max_page
        self.title = title
        self.stat_counter = stat_counter

        self.page = 0

        setting = SettingsManager("user", user_id).get("preferred_leaderboard_output_type")
        self.is_fancy = True if setting == "image" else False


    @discord.ui.button(emoji=UI_EMOJI_MAP["left_arrow"], row=1)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page < 0:
            self.page = 0
            await interaction.response.send_message("You are at the first page!", ephemeral=True)
        else:
            await self.update(interaction)
    

    @discord.ui.button(emoji=UI_EMOJI_MAP["right_arrow"], row=1)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page > self.max_page:
            self.page = self.max_page
            await interaction.response.send_message("You are at the last page!", ephemeral=True)
        else:
            await self.update(interaction)
    

    @discord.ui.button(emoji="✨", row=1)
    async def fancy_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.is_fancy = not self.is_fancy
        await self.update(interaction)


    async def update(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.is_fancy:
            board = await build_board(self.data, self.page)
            await interaction.edit_original_response(embed=None, view=self, attachments=[board])
        else:
            start = self.page * 10
            end = start + 10
            sliced = self.data[start:end]

            for i in range(len(sliced)):
                sliced[i] = [f"{i+start+1}.", sliced[i][0], sliced[i][1]]
            
            embed = TextTableEmbed(["Rank", "Name", self.stat_counter], sliced, title=self.title, color=0x333333)
            await interaction.edit_original_response(embed=embed, view=self, attachments=[])



async def build_board(data: list[tuple[str, int]], page: int) -> discord.Embed:
    """
    Builds a leaderboard-like image.

    Args:
        title (str): The title of the leaderboard.
        entries (list): List of tuples in the form [(name, value), ...].
        icon_url (str, optional): URL of an image to display as a corner icon.

    Returns:
        discord.File: The image rendered as a Discord uploadable file.
    """
        
    data_list = []
    for i in range(len(data)):
        data_list.append([i+1, data[i][0], data[i][1]])

        
    rank_margin = 45
    model_margin = 115
    name_margin = 205
    value_margin = 685

    font = ImageFont.truetype("MinecraftRegular.ttf", 20)
    board = Image.new("RGBA", (730, 695), (110, 110, 110))
    overlay = Image.open("assets/board_segment.png")
    overlay2 = Image.open("assets/board_segment_dark.png")
    overlay_toggle = True
    draw = ImageDraw.Draw(board)

    names = []
    for i in data: names.append(i[0])
    await fetch_player_busts(names)

    for i in range(1, 11):
        stat = data_list[(i-1)+(page*10)]
        height = ((i-1)*69)+5
        board.paste(overlay if overlay_toggle else overlay2, (5, height), overlay)
        overlay_toggle = not overlay_toggle

        try:
            model_img = Image.open(f"/tmp/{stat[1]}_model.png", 'r')
            model_img = model_img.resize((64, 64))
        except Exception as e:
            model_img = Image.open(f"assets/unknown_model.png", 'r')
            model_img = model_img.resize((64, 64))
            print(f"Error loading image: {e}")

        board.paste(model_img, (model_margin, height), model_img)
        draw.text((rank_margin, height+22), "#"+str(stat[0]), font=font)
        draw.text((name_margin, height+22), str(stat[1]), font=font)
        draw.text((value_margin, height+22), str(stat[2]), font=font, anchor="rt")


    board.save("/tmp/board.png")

    return discord.File("/tmp/board.png", filename="board.png")
