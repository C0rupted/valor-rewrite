import discord


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
    def __init__(self, title: str = "", description: str = "", footer: str = None):
        super().__init__(title=title, description=description, color=discord.Color.blurple())
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

        if color:
            self.color = color
        else:
            self.color = discord.Color.teal()
            
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

        table = f"```isbl\n{header_row}\n{separator}\n" + "\n".join(data_rows) + "\n```"
        self.description = table




