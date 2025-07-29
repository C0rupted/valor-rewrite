import discord

from util.mappings import UI_EMOJI_MAP


class ErrorEmbed(discord.Embed):
    """
    Basic error report embed.
    Usage: ErrorEmbed(description: str)
    """
    def __init__(self, description: str ="An error occurred.", footer: str = None):
        super().__init__(title="Error!", description=description, color=discord.Color.red())
        if footer:
            self.set_footer(text=footer)


class InfoEmbed(discord.Embed):
    """
    Basic informative embed.
    Usage: ErrorEmbed(description: str)
    """
    def __init__(self, title: str = "", description: str = "", footer: str = None, color: discord.Colour = discord.Color.blurple()):
        super().__init__(title=title, description=description, color=color)
        if footer:
            self.set_footer(text=footer)


class TextTableEmbed(discord.Embed):
    """
    Embed that displays a table of text with aligned columns.
    Usage: TextTableEmbed(headers: List[str], rows: List[List[str]])
    """
    def __init__(self, headers: list[str], rows: list[list[str]], title: str = None, footer: str = None, color: discord.Colour = None):
        super().__init__()

        if title:
            self.title = title
        self.color = color or discord.Color.teal()
        if footer:
            self.set_footer(text=footer)

        # Calculate column widths
        column_widths = [max(len(str(item)) for item in col) for col in zip(headers, *rows)]

        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        # Build header and separator
        header_row = row_format(headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(headers)))

        # Format all data rows
        data_rows = [row_format(row) for row in rows]

        table = [header_row, separator] + data_rows
        total_text = "```isbl\n" + "\n".join(table) + "\n```"

        if len(total_text) <= 4096:
            self.description = total_text
        else:
            chunk = []
            chunk_len = 0
            for row in table:
                row_len = len(row) + 1  # +1 for newline
                if chunk_len + row_len > 1010:  # Slight buffer for the code block wrapper
                    self.add_field(name="", value=f"```isbl\n{'\n'.join(chunk)}\n```", inline=False)
                    chunk = [row]
                    chunk_len = row_len
                else:
                    chunk.append(row)
                    chunk_len += row_len

            if chunk:
                self.add_field(name="", value=f"```isbl\n{'\n'.join(chunk)}\n```", inline=False)


class PaginatedTextTableEmbed(discord.ui.View):
    """
    Paginated embed that displays a table of text with aligned columns.
    Usage: PaginatedTextTableEmbed.send(headers: List[str], rows: List[List[str]])
    """
    def __init__(self, headers: list[str], rows: list[list[str]], title: str = None, footer: str = None, color: discord.Colour = None, rows_per_page: int = 10, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.headers = headers
        self.rows = rows
        self.title = title
        self.footer = footer
        self.color = color or discord.Color.teal()
        self.rows_per_page = rows_per_page
        self.page = 0
        self.total_pages = (len(rows) + rows_per_page - 1) // rows_per_page
        self.message = None

        # Buttons
        self.prev_button = discord.ui.Button(emoji=UI_EMOJI_MAP["left_arrow"], style=discord.ButtonStyle.gray)
        self.prev_button.callback = self.go_previous
        self.next_button = discord.ui.Button(emoji=UI_EMOJI_MAP["right_arrow"], style=discord.ButtonStyle.gray)
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    def format_page(self, page: int) -> discord.Embed:
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        page_rows = self.rows[start:end]

        column_widths = [max(len(str(item)) for item in col) for col in zip(self.headers, *self.rows)]
        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(self.headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(self.headers)))
        data_rows = [row_format(row) for row in page_rows]

        table = f"```isbl\n{header_row}\n{separator}\n" + "\n".join(data_rows) + "\n```"

        embed = discord.Embed(title=self.title, description=table, color=self.color)
        if self.footer:
            embed.set_footer(text=f"{self.footer} | Page {page + 1}/{self.total_pages}")
        else:
            embed.set_footer(text=f"Page {page + 1}/{self.total_pages}")
        return embed

    async def go_previous(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the first page!", ephemeral=True)

    async def go_next(self, interaction: discord.Interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the last page!", ephemeral=True)

    @classmethod
    async def send(
        cls,
        interaction: discord.Interaction,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        footer: str = None,
        color: discord.Colour = None,
        rows_per_page: int = 10,
    ):
        view = cls(headers, rows, title, footer, color, rows_per_page)
        embed = view.format_page(0)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
        
        return view


class PaginatedTextTable(discord.ui.View):
    """
    Paginated text table that displays with aligned columns.
    Usage: PaginatedTextTable.send(headers: List[str], rows: List[List[str]])
    """
    def __init__(self, headers: list[str], rows: list[list[str]], title: str = None, footer: str = None, rows_per_page: int = 10):
        super().__init__(timeout=60)
        self.headers = headers
        self.rows = rows
        self.title = title
        self.footer = footer
        self.rows_per_page = rows_per_page
        self.page = 0
        self.total_pages = (len(rows) + rows_per_page - 1) // rows_per_page
        self.message = None

        # Buttons
        self.prev_button = discord.ui.Button(emoji=UI_EMOJI_MAP["left_arrow"], style=discord.ButtonStyle.gray)
        self.prev_button.callback = self.go_previous
        self.next_button = discord.ui.Button(emoji=UI_EMOJI_MAP["right_arrow"], style=discord.ButtonStyle.gray)
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)


    def format_page(self, page: int) -> discord.Embed:
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        page_rows = self.rows[start:end]

        column_widths = [max(len(str(item)) for item in col) for col in zip(self.headers, *self.rows)]
        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(self.headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(self.headers)))
        data_rows = [row_format(row) for row in page_rows]

        table = f"```isbl\n{self.title}\n \n{header_row}\n{separator}\n" + "\n".join(data_rows)

        if self.footer:
            table += f"\n \n{self.footer} | Page {page + 1}/{self.total_pages}"
        else:
            table += f"\n \nPage {page + 1}/{self.total_pages}"

        table +=  "\n```"

        return table

    async def go_previous(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(content=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the first page!", ephemeral=True)

    async def go_next(self, interaction: discord.Interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
            await interaction.response.edit_message(content=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the last page!", ephemeral=True)

    @classmethod
    async def send(
        cls,
        interaction: discord.Interaction,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        footer: str = None,
        rows_per_page: int = 10,
    ):
        view = cls(headers, rows, title, footer, rows_per_page)
        table = view.format_page(0)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(table, view=view)
        else:
            await interaction.response.send_message(table, view=view)
            view.message = await interaction.original_response()
        
        return view





