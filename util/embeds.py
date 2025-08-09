import discord

from util.mappings import UI_EMOJI_MAP



class ErrorEmbed(discord.Embed):
    """
    Basic error report embed.

    Usage:
        ErrorEmbed(description: str, footer: str | None = None)

    Args:
        description (str): The error message to display.
        footer (str, optional): Optional footer text.
    """
    def __init__(self, description: str = "An error occurred.", footer: str = None):
        # Initialize the embed with title "Error!", red color, and description text
        super().__init__(title="Error!", description=description, color=discord.Color.red())
        if footer:
            self.set_footer(text=footer)



class InfoEmbed(discord.Embed):
    """
    Basic informative embed.

    Usage:
        InfoEmbed(title: str, description: str, footer: str | None = None, color: discord.Colour = discord.Color.blurple())

    Args:
        title (str): Embed title.
        description (str): Main description text.
        footer (str, optional): Optional footer text.
        color (discord.Colour, optional): Embed color. Defaults to blurple.
    """
    def __init__(
        self,
        title: str = "",
        description: str = "",
        footer: str = None,
        color: discord.Colour = discord.Color.blurple(),
    ):
        # Initialize embed with given title, description, and color
        super().__init__(title=title, description=description, color=color)
        if footer:
            self.set_footer(text=footer)



class TextTableEmbed(discord.Embed):
    """
    Embed displaying a text-based table with aligned columns.

    Usage:
        TextTableEmbed(headers: list[str], rows: list[list[str]], title: str = None, footer: str = None, color: discord.Colour = None)

    Args:
        headers (list[str]): List of column header strings.
        rows (list[list[str]]): List of data rows, each a list of strings.
        title (str, optional): Embed title.
        footer (str, optional): Footer text.
        color (discord.Colour, optional): Embed color.
    """
    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        footer: str = None,
        color: discord.Colour = None,
    ):
        super().__init__()
        if title:
            self.title = title
        self.color = color or discord.Color.teal()
        if footer:
            self.set_footer(text=footer)

        # Calculate max width per column by checking header + all rows
        column_widths = [max(len(str(item)) for item in col) for col in zip(headers, *rows)]

        def row_format(row: list[str]) -> str:
            # Formats a single row with columns left-aligned, padded to column widths
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(headers)
        # Separator line uses heavy box drawing characters
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(headers)))

        data_rows = [row_format(row) for row in rows]
        table = [header_row, separator] + data_rows

        # Combine rows into a code block string
        total_text = "```isbl\n" + "\n".join(table) + "\n```"

        # If under Discord embed description length limit, put entire table in description
        if len(total_text) <= 4096:
            self.description = total_text
        else:
            # If too long, split into multiple fields to avoid embed size limits
            chunk = []
            chunk_len = 0
            for row in table:
                row_len = len(row) + 1  # Include newline char
                if chunk_len + row_len > 1010:  # Leave buffer for code block syntax
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
    A Discord UI View that displays a paginated embed with a text table.

    Usage:
        await PaginatedTextTableEmbed.send(interaction, headers, rows, title, footer, color, rows_per_page)

    Args:
        headers (list[str]): List of column headers.
        rows (list[list[str]]): List of rows (each row is a list of strings).
        title (str, optional): Embed title.
        footer (str, optional): Footer text.
        color (discord.Colour, optional): Embed color.
        rows_per_page (int, optional): Number of rows per page (default 10).
        timeout (int, optional): Interaction timeout in seconds.
    """
    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        footer: str = None,
        color: discord.Colour = None,
        rows_per_page: int = 10,
        timeout: int = 60,
    ):
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

        # Create previous and next buttons with appropriate emoji and callback handlers
        self.prev_button = discord.ui.Button(emoji=UI_EMOJI_MAP["left_arrow"], style=discord.ButtonStyle.gray)
        self.prev_button.callback = self.go_previous
        self.next_button = discord.ui.Button(emoji=UI_EMOJI_MAP["right_arrow"], style=discord.ButtonStyle.gray)
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)


    def format_page(self, page: int) -> discord.Embed:
        """
        Creates an embed representing the table page requested.

        Args:
            page (int): Page index to format.

        Returns:
            discord.Embed: Embed containing formatted table page.
        """
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        page_rows = self.rows[start:end]

        # Calculate max width per column for alignment
        column_widths = [max(len(str(item)) for item in col) for col in zip(self.headers, *self.rows)]

        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(self.headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(self.headers)))
        data_rows = [row_format(row) for row in page_rows]

        table = f"```isbl\n{header_row}\n{separator}\n" + "\n".join(data_rows) + "\n```"

        embed = discord.Embed(title=self.title, description=table, color=self.color)
        footer_text = f"{self.footer} | Page {page + 1}/{self.total_pages}" if self.footer else f"Page {page + 1}/{self.total_pages}"
        embed.set_footer(text=footer_text)

        return embed


    async def go_previous(self, interaction: discord.Interaction):
        """
        Handler for previous page button click.

        Sends previous page if available; otherwise sends ephemeral warning.
        """
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the first page!", ephemeral=True)


    async def go_next(self, interaction: discord.Interaction):
        """
        Handler for next page button click.

        Sends next page if available; otherwise sends ephemeral warning.
        """
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
        """
        Convenience method to create and send the paginated embed to an interaction.

        Args:
            interaction (discord.Interaction): The interaction to respond to.
            headers (list[str]): Table column headers.
            rows (list[list[str]]): Table rows.
            title (str, optional): Embed title.
            footer (str, optional): Footer text.
            color (discord.Colour, optional): Embed color.
            rows_per_page (int, optional): Rows per page.

        Returns:
            PaginatedTextTableEmbed: The instantiated view for further manipulation.
        """
        view = cls(headers, rows, title, footer, color, rows_per_page)
        embed = view.format_page(0)

        # Check if interaction already responded to decide how to send message
        if interaction.response.is_done():
            view.message = await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()

        return view



class PaginatedTextTable(discord.ui.View):
    """
    A paginated view that displays text tables using message content (not embeds).

    Usage:
        await PaginatedTextTable.send(interaction, headers, rows, title, footer, rows_per_page)

    Args:
        headers (list[str]): Column headers.
        rows (list[list[str]]): Table rows.
        title (str, optional): Table title.
        footer (str, optional): Footer text.
        rows_per_page (int, optional): Rows per page (default 10).
    """
    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        footer: str = None,
        rows_per_page: int = 10,
    ):
        super().__init__(timeout=60)
        self.headers = headers
        self.rows = rows
        self.title = title
        self.footer = footer
        self.rows_per_page = rows_per_page

        self.page = 0
        self.total_pages = (len(rows) + rows_per_page - 1) // rows_per_page
        self.message = None

        # Setup previous and next buttons with callback handlers
        self.prev_button = discord.ui.Button(emoji=UI_EMOJI_MAP["left_arrow"], style=discord.ButtonStyle.gray)
        self.prev_button.callback = self.go_previous
        self.next_button = discord.ui.Button(emoji=UI_EMOJI_MAP["right_arrow"], style=discord.ButtonStyle.gray)
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)


    def format_page(self, page: int) -> str:
        """
        Formats the text table page as a code block string.

        Args:
            page (int): Page number to format.

        Returns:
            str: Formatted text table.
        """
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        page_rows = self.rows[start:end]

        # Calculate max width per column for alignment
        column_widths = [max(len(str(item)) for item in col) for col in zip(self.headers, *self.rows)]

        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(self.headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(self.headers)))
        data_rows = [row_format(row) for row in page_rows]

        # Build the table string with optional title and footer lines
        table = f"```isbl\n{self.title}\n \n{header_row}\n{separator}\n" + "\n".join(data_rows)

        if self.footer:
            table += f"\n \n{self.footer} | Page {page + 1}/{self.total_pages}"
        else:
            table += f"\n \nPage {page + 1}/{self.total_pages}"

        table += "\n```"

        return table


    async def go_previous(self, interaction: discord.Interaction):
        """
        Handler for previous page button click.

        Edits message content to previous page or sends ephemeral message if at first page.
        """
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(content=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the first page!", ephemeral=True)


    async def go_next(self, interaction: discord.Interaction):
        """
        Handler for next page button click.

        Edits message content to next page or sends ephemeral message if at last page.
        """
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
        """
        Convenience method to create and send the paginated text table to an interaction.

        Args:
            interaction (discord.Interaction): Interaction to respond to.
            headers (list[str]): Column headers.
            rows (list[list[str]]): Table rows.
            title (str, optional): Table title.
            footer (str, optional): Footer text.
            rows_per_page (int, optional): Rows per page.

        Returns:
            PaginatedTextTable: The instantiated view.
        """
        view = cls(headers, rows, title, footer, rows_per_page)
        table = view.format_page(0)

        # Send or follow-up depending on response state
        if interaction.response.is_done():
            view.message = await interaction.followup.send(table, view=view)
        else:
            await interaction.response.send_message(table, view=view)
            view.message = await interaction.original_response()

        return view



class PaginatedFieldedTextTableEmbed(discord.ui.View):
    """
    A paginated embed that displays multiple sectioned tables with aligned columns.

    Usage:
        await PaginatedFieldedTextTableEmbed.send(interaction, headers, rows_by_section, ...)

    Args:
        headers (list[str]): Column headers.
        rows_by_section (dict[str, list[list[str]]]): Dictionary mapping section titles to their rows.
        title (str, optional): Embed title.
        footer (str, optional): Footer text.
        color (discord.Colour, optional): Embed color.
        rows_per_page (int, optional): Rows per page.
        timeout (int, optional): Interaction timeout.
    """
    def __init__(
        self,
        headers: list[str],
        rows_by_section: dict[str, list[list[str]]],
        title: str = None,
        footer: str = None,
        color: discord.Colour = None,
        rows_per_page: int = 10,
        timeout: int = 60,
    ):
        super().__init__(timeout=timeout)

        self.headers = headers
        self.rows_by_section = rows_by_section
        self.title = title
        self.footer = footer
        self.color = color or discord.Color.teal()
        self.rows_per_page = rows_per_page
        self.page = 0

        # Flatten rows into a list of (section, row) tuples for easier pagination
        self.sectioned_rows: list[tuple[str, list[str]]] = []
        for section, rows in rows_by_section.items():
            for row in rows:
                self.sectioned_rows.append((section, row))

        self.total_pages = (len(self.sectioned_rows) + rows_per_page - 1) // rows_per_page
        self.message = None

        # Previous and next page buttons with callbacks
        self.prev_button = discord.ui.Button(emoji=UI_EMOJI_MAP["left_arrow"], style=discord.ButtonStyle.gray)
        self.prev_button.callback = self.go_previous
        self.next_button = discord.ui.Button(emoji=UI_EMOJI_MAP["right_arrow"], style=discord.ButtonStyle.gray)
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)


    def format_page(self, page: int) -> discord.Embed:
        """
        Formats the embed content for the requested page, grouping rows by section.

        Args:
            page (int): Page number to format.

        Returns:
            discord.Embed: Embed containing formatted sectioned tables.
        """
        start = page * self.rows_per_page
        end = start + self.rows_per_page
        sectioned_slice = self.sectioned_rows[start:end]

        # Compute max width per column over all rows
        column_widths = [max(len(str(item)) for item in col) for col in zip(self.headers, *(r for _, r in self.sectioned_rows))]

        def row_format(row: list[str]) -> str:
            return " ┃ ".join(f"{col:<{column_widths[i]}}" for i, col in enumerate(row))

        header_row = row_format(self.headers)
        separator = "━╋━".join("━" * column_widths[i] for i in range(len(self.headers)))

        # Group rows by their section for this page
        sections: dict[str, list[str]] = {}
        for section, row in sectioned_slice:
            sections.setdefault(section, []).append(row_format(row))

        embed = discord.Embed(title=self.title, color=self.color)

        # Add each section as an embed field with formatted table
        for section, formatted_rows in sections.items():
            table = f"```isbl\n{header_row}\n{separator}\n" + "\n".join(formatted_rows) + "\n```"
            embed.add_field(name=section, value=table, inline=False)

        footer_text = f"{self.footer} | Page {page + 1}/{self.total_pages}" if self.footer else f"Page {page + 1}/{self.total_pages}"
        embed.set_footer(text=footer_text)

        return embed


    async def go_previous(self, interaction: discord.Interaction):
        """
        Handler for previous page button click.

        Sends previous page or ephemeral warning if on first page.
        """
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.format_page(self.page), view=self)
        else:
            await interaction.response.send_message("You are at the first page!", ephemeral=True)

    async def go_next(self, interaction: discord.Interaction):
        """
        Handler for next page button click.

        Sends next page or ephemeral warning if on last page.
        """
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
        rows_by_section: dict[str, list[list[str]]],
        title: str = None,
        footer: str = None,
        color: discord.Colour = None,
        rows_per_page: int = 10,
    ):
        """
        Convenience method to create and send the paginated fielded embed.

        Args:
            interaction (discord.Interaction): The interaction to respond to.
            headers (list[str]): Table headers.
            rows_by_section (dict[str, list[list[str]]]): Section titles mapped to their rows.
            title (str, optional): Embed title.
            footer (str, optional): Footer text.
            color (discord.Colour, optional): Embed color.
            rows_per_page (int, optional): Rows per page.

        Returns:
            PaginatedFieldedTextTableEmbed: The instantiated view.
        """
        view = cls(headers, rows_by_section, title, footer, color, rows_per_page)
        embed = view.format_page(0)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()

        return view


