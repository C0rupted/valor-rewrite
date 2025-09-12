import discord, io, math
from PIL import Image, ImageDraw, ImageFont

from core.settings import SettingsManager
from util.embeds import TextTableEmbed, PaginatedTextTable
from util.guilds import guild_tags_from_names
from util.mappings import UI_EMOJI_MAP
from util.requests import fetch_player_busts


FONT_PATH = "assets/fonts/MinecraftRegular.ttf"


class BoardView(discord.ui.View):
    """
    A custom Discord UI View to display a simple paginated leaderboard.

    Supports two display modes:
    - Fancy image-based leaderboard using `build_board`
    - Plain text embed leaderboard

    Pagination controls allow navigating between pages of leaderboard data.

    Attributes:
        user_id (int): Discord user ID to fetch personal settings.
        data (list of tuples): Leaderboard data as (name, value).
        title (str): Title of the leaderboard embed.
        max_page (int): Maximum page number for pagination.
        stat_counter (str): Label for the stat column.
        is_guild_board (bool): Whether this is a guild leaderboard (affects image).
        use_text_embed (bool): Whether to use text embed fallback.
        headers (list): Column headers for the leaderboard.
        page (int): Current page index.
        is_fancy (bool): Whether to use the image mode based on user setting.
    """

    def __init__(
        self,
        user_id,
        data: list[tuple[str, int]],
        title: str = "Leaderboard",
        max_page: int = None,
        stat_counter: str = "Value",
        is_guild_board: bool = False,
        use_text_embed: bool = True,
        headers: list[str] = None,
    ):
        super().__init__()
        self.user_id = user_id
        self.data = data
        self.max_page = max_page if max_page is not None else math.ceil(len(data) / 10)
        self.title = title
        if headers:
            # Use custom headers prepended by "Rank"
            self.headers = ["Rank"] + headers
        else:
            # Default headers: Rank, Name, stat counter label
            self.headers = ["Rank", "Name", stat_counter]

        self.stat_counter = stat_counter
        self.is_guild_board = is_guild_board
        self.use_text_embed = use_text_embed

        self.page = 0  # Start on first page

        # Fetch user setting to decide if image mode or text embed is used
        setting = SettingsManager("user", user_id).get("preferred_leaderboard_output_type")
        self.is_fancy = True if setting == "image" else False


    @discord.ui.button(emoji=UI_EMOJI_MAP["left_arrow"], row=1)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handler for the 'previous page' button.
        Moves to the previous page if possible; else sends an ephemeral warning.
        """
        self.page -= 1
        if self.page < 0:
            self.page = 0
            await interaction.response.send_message("You are at the first page!", ephemeral=True)
        else:
            await self.update(interaction)


    @discord.ui.button(emoji=UI_EMOJI_MAP["right_arrow"], row=1)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handler for the 'next page' button.
        Moves to the next page if possible; else sends an ephemeral warning.
        """
        self.page += 1
        if self.page > self.max_page:
            self.page = self.max_page
            await interaction.response.send_message("You are at the last page!", ephemeral=True)
        else:
            await self.update(interaction)


    async def update(self, interaction: discord.Interaction):
        """
        Updates the message with the current page of leaderboard data.

        Chooses to send either a fancy image board or a text embed based on user settings.
        """
        await interaction.response.defer()

        if self.is_fancy:
            # Build the image leaderboard for the current page and send it
            board = await build_board(self.data, self.page, is_guild_board=self.is_guild_board)
            await interaction.edit_original_response(embed=None, view=self, attachments=[board])
        else:
            # Prepare slice of data for current page (10 entries per page)
            start = self.page * 10
            end = start + 10
            sliced = self.data[start:end]

            # Add ranks as string prefix to each row
            for i in range(len(sliced)):
                sliced[i] = [f"{i+start+1}.", sliced[i][0], sliced[i][1]]

            if self.use_text_embed:
                # Send paginated text embed leaderboard
                embed = TextTableEmbed(self.headers, sliced, title=self.title, color=0x333333)
                await interaction.edit_original_response(embed=embed, view=self, attachments=[])
            else:
                # Alternate fallback (rarely used)
                await PaginatedTextTable.send(interaction, self.headers, self.data, "Warcount sum for guilds")



class WarcountBoardView(discord.ui.View):
    """
    A custom Discord UI View for a detailed warcount leaderboard supporting multiple class columns.

    Supports paginated image or text table display, based on user settings.

    Attributes:
        user_id (int): Discord user ID to fetch personal settings.
        headers (list): Column headers, including rank, name, guild, class counts, total.
        rows (list of tuples): Data rows containing player warcounts.
        listed_classes (list of str): Classes to show (ARCHER, WARRIOR, etc.).
        is_guild_board (bool): Whether this is a guild leaderboard (affects image).
        page (int): Current page index.
        is_fancy (bool): Whether to use image output mode.
        max_pages (int): Maximum page count based on data length.
    """

    def __init__(
        self,
        user_id,
        headers,
        rows,
        listed_classes,
        is_guild_board: bool = False,
        timeout=60,
    ):
        super().__init__(timeout=timeout)
        self.listed_classes = listed_classes

        self.page = 0
        self.headers = headers
        self.data = rows
        self.user_id = user_id

        self.is_guild_board = is_guild_board

        # User preference for image or text output
        setting = SettingsManager("user", user_id).get("preferred_leaderboard_output_type")
        self.is_fancy = True if setting == "image" else False

        # Compute max pages needed for pagination (10 rows per page)
        self.max_pages = math.ceil(len(rows) / 10)


    async def update_message(self, interaction: discord.Interaction):
        """
        Updates the leaderboard message with the current page content.

        Sends either an image-based warcount board or a formatted text table.
        """
        if self.is_fancy:
            await interaction.response.defer()
            content = await build_warcount_board(self.data, self.page, self.listed_classes)
            await interaction.edit_original_response(content="", view=self, attachments=[content])
        else:
            # Slice rows for current page
            start, end = self.page * 10, (self.page + 1) * 10
            sliced = self.data[start:end]

            # Calculate widths for each column based on headers
            widths = [len(h) for h in self.headers]
            fmt = ' ┃ '.join(f'%{w}s' for w in widths)

            lines = [fmt % tuple(self.headers)]  # header line
            # Create a separator line replacing '┃' with '╋' and others with '━'
            separator = ''.join('╋' if c == '┃' else '━' for c in lines[0])
            lines.append(separator)

            # Append each row formatted with left-justified columns
            for row in sliced:
                lines.append(' ┃ '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
            lines.append(separator)

            content = '```isbl\n' + '\n'.join(lines) + '```'
            await interaction.response.edit_message(content=content, view=self, attachments=[])


    @discord.ui.button(emoji=UI_EMOJI_MAP["left_arrow"])
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handler for 'previous page' button.

        Moves back one page if possible; otherwise defers without message.
        """
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()


    @discord.ui.button(emoji=UI_EMOJI_MAP["right_arrow"])
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handler for 'next page' button.

        Moves forward one page if possible; otherwise defers without message.
        """
        if self.page < self.max_pages - 1:
            self.page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()



async def build_board(data: list[tuple[str, int]], page: int, is_guild_board: bool = False) -> discord.File:
    """
    Builds a graphical leaderboard image with player/guild icons, ranks, names, and stat values.

    Args:
        data (list of tuples): Leaderboard entries as (name, value).
        page (int): Current page index for pagination.
        is_guild_board (bool): If True, render guild icons instead of player busts.

    Returns:
        discord.File: A Discord file object containing the generated PNG image.
    """
    # Prepare data with ranks enumerated starting from 1
    data_list = []
    for i in range(len(data)):
        data_list.append([i + 1, data[i][0], data[i][1]])

    # Margins / X-coordinates for drawing elements
    rank_margin = 45
    model_margin = 115
    name_margin = 205
    value_margin = 685

    # Load Minecraft font at size 20
    font = ImageFont.truetype("MinecraftRegular.ttf", 20)

    # Create base image with grey background
    board = Image.new("RGBA", (730, 695), (110, 110, 110))

    # Load alternating overlay images for row backgrounds
    overlay = Image.open("assets/board_segment.png")
    overlay2 = Image.open("assets/board_segment_dark.png")
    overlay_toggle = True

    draw = ImageDraw.Draw(board)

    # Extract names from data to fetch icons
    names = []
    for i in data_list:
        names.append(i[1])

    # Fetch guild tags or player busts depending on board type
    if is_guild_board:
        tags = (await guild_tags_from_names(names))[0]
    else:
        await fetch_player_busts(names)

    # Render 10 entries per page
    for i in range(1, 11):
        try:
            stat = data_list[(i - 1) + (page * 10)]
        except IndexError:
            # No more entries on this page
            continue

        height = ((i - 1) * 69) + 5  # Y coordinate for this row

        # Paste alternating background segment
        board.paste(overlay if overlay_toggle else overlay2, (5, height), overlay)
        overlay_toggle = not overlay_toggle

        # Load icon image based on guild or player
        if is_guild_board:
            tag = tags[names.index(stat[1])]
            try:
                model_img = Image.open(f"assets/icons/guilds/{tag}.png", 'r')
                model_img = model_img.crop(model_img.getbbox())
            except FileNotFoundError:
                # Use blank placeholder if guild icon missing
                model_img = Image.new("RGBA", (54, 54))
        else:
            try:
                # Player bust cached image
                model_img = Image.open(f"/tmp/{stat[1]}_model.png", 'r')
            except Exception as e:
                # Fallback unknown image with error logged
                model_img = Image.open(f"assets/unknown_model.png", 'r')
                print(f"Error loading image: {e}")

        # Resize icon to 64x64 and paste
        model_img = model_img.resize((64, 64))
        board.paste(model_img, (model_margin, height), model_img)

        # Draw rank, name, and stat value text
        draw.text((rank_margin, height + 22), "#" + str(stat[0]), font=font)
        draw.text((name_margin, height + 22), str(stat[1]), font=font)
        draw.text((value_margin, height + 22), str(stat[2]), font=font, anchor="rt")

    # Save image to bytes buffer and create Discord file
    with io.BytesIO() as img_binary:
        board.save(img_binary, 'PNG')
        img_binary.seek(0)
        file = discord.File(fp=img_binary, filename="board.png")

    return file


async def build_warcount_board(
    data: list[tuple],
    page: int,
    listed_classes: list[str],
    is_guild_board: bool = False,
) -> discord.File:
    """
    Builds a detailed warcount leaderboard image showing warcounts per class and totals.

    Args:
        data (list of tuples): Warcount data rows.
        page (int): Current page index.
        listed_classes (list of str): Classes to show (e.g. ARCHER, WARRIOR).
        is_guild_board (bool): Whether this is a guild leaderboard (affects icons).

    Returns:
        discord.File: Discord file containing the rendered PNG leaderboard image.
    """
    # Extract only the 10 rows for current page
    start = page * 10
    end = start + 10
    sliced = data[start:end]

    # Load base template image for warcount leaderboard
    img = Image.open("assets/warcount_template.png")
    draw = ImageDraw.Draw(img)

    # Font sizes for different elements
    name_fontsize = 20
    text_fontsize = 16
    total_fontsize = 18

    # Load Minecraft fonts
    name_font = ImageFont.truetype("assets/MinecraftRegular.ttf", name_fontsize)
    text_font = ImageFont.truetype("assets/MinecraftRegular.ttf", text_fontsize)
    total_font = ImageFont.truetype("assets/MinecraftRegular.ttf", total_fontsize)

    # Collect names for icon fetching
    names = []
    for i in sliced:
        names.append(i[1])

    # Fetch guild tags or player busts as applicable
    if is_guild_board:
        tags = (await guild_tags_from_names(names))[0]
    else:
        await fetch_player_busts(names)

    i = 1
    for row in sliced:
        # Calculate y-position for this row (with spacing)
        y = ((57 * (i / 2)) + (59 * (i / 2))) + 27

        # Draw rank number (right-middle aligned)
        draw.text((62, y), f"{row[0]}.", "white", total_font, anchor="rm")
        # Draw player/guild name (left-middle aligned)
        draw.text((153, y), row[1], "white", name_font, anchor="lm")

        # Load and paste guild or player icon for this row
        if is_guild_board:
            tag = tags[names.index(row[1])]
            try:
                model_img = Image.open(f"assets/icons/guilds/{tag}.png", 'r')
                model_img = model_img.crop(model_img.getbbox())
            except FileNotFoundError:
                model_img = Image.new("RGBA", (54, 54))
        else:
            try:
                model_img = Image.open(f"/tmp/{row[1]}_model.png", 'r')
            except Exception as e:
                model_img = Image.open(f"assets/unknown_model.png", 'r')
                print(f"Error loading image: {e}")

        # Resize and paste the icon (54x54) slightly above y
        model_img = model_img.resize((54, 54))
        img.paste(model_img, (84, int(y) - 29), model_img)

        # Draw total warcount (middle-middle aligned)
        draw.text((445, y), row[2], "white", total_font, anchor="mm")

        x = 0  # Offset for class warcount columns

        # Draw warcounts for each listed class in fixed horizontal positions
        if "ARCHER" in listed_classes:
            draw.text((532, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "WARRIOR" in listed_classes:
            draw.text((593, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "MAGE" in listed_classes:
            draw.text((658, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "ASSASSIN" in listed_classes:
            draw.text((718, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1
        if "SHAMAN" in listed_classes:
            draw.text((780, y), str(row[3 + x]), "white", text_font, anchor="mm")
            x += 1

        # Draw total warcount sum at the right end, left-middle aligned
        draw.text((827, y), str(row[3 + x]), "white", total_font, anchor="lm")

        i += 1

    # Save rendered image to bytes buffer and wrap in Discord file
    with io.BytesIO() as img_binary:
        img.save(img_binary, 'PNG')
        img_binary.seek(0)
        file = discord.File(fp=img_binary, filename="board.png")

    return file
