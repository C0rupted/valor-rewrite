import discord

from discord import app_commands
from discord.ext import commands

from util.embeds import ErrorEmbed
from util.mappings import TERRITORY_DAMAGE_VALUES, TERRITORY_ATTACK_VALUES, TERRITORY_HEALTH_VALUES, TERRITORY_DEFENCE_VALUES


class Utilities(commands.GroupCog, name="utilities"):
    """
    Group cog providing various miscellaneous utilities.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="calculate_territory_defences",
        description="Calculate tower stats based on buffs and HQ status."
    )
    @app_commands.describe(
        buffs="Four upgrade levels separated by commas (e.g. 4,8,2,11 or 4x11)",
        conns="Number of connections (default 0)",
        exts="Number of externals (default 0)",
        is_hq="Is this an HQ territory? (default True)"
    )
    async def calculate_territory_defences(
        self,
        interaction: discord.Interaction,
        conns: int = 0,
        exts: int = 0,
        buffs: str = "4x11",
        is_hq: bool = True
    ):
        """
        Slash command to calculate territory tower defense stats given buff levels, connection counts, and HQ status.

        Parameters:
        - buffs (str): String representing four buff levels, either "4x11" format (all equal) or comma-separated (e.g. "4,8,2,11").
        - conns (int): Number of connections to the territory (default 0).
        - exts (int): Number of externals connected (default 0).
        - is_hq (bool): Whether the territory is an HQ (default True).

        Calculates and returns HP, damage ranges, defense percentage, attack speed, effective HP, and DPS.
        """

        # Attempt to parse the buffs string input
        try:
            # If buffs starts with "4x", interpret it as all four buffs equal to the value after 'x'
            if buffs.strip().startswith("4x"):
                parts = buffs.split("x")
                if len(parts) != 2:
                    raise ValueError()
                buffs_list = [int(parts[1])] * 4
            else:
                # Otherwise expect comma-separated values for each buff level
                buffs_list = list(map(int, buffs.split(",")))
                if len(buffs_list) != 4:
                    raise ValueError()
        except Exception:
            # Send error message if input format is invalid
            return await interaction.response.send_message(
                embed=ErrorEmbed("Please use either `4x11` or `4,8,2,11` format."),
                ephemeral=True
            )

        # Unpack the individual buff levels
        dmg_lvl, atk_lvl, hp_lvl, def_lvl = buffs_list

        # Validate that all buff levels are within the valid range 0 to 11 inclusive
        if not all(0 <= b <= 11 for b in buffs_list):
            return await interaction.response.send_message(
                embed=ErrorEmbed("Each buff level must be between 0 and 11."),
                ephemeral=True
            )

        # Lookup the base stats for each buff level from mappings
        damage = TERRITORY_DAMAGE_VALUES[dmg_lvl]
        atk_speed = TERRITORY_ATTACK_VALUES[atk_lvl]
        base_hp = TERRITORY_HEALTH_VALUES[hp_lvl]
        def_percent = TERRITORY_DEFENCE_VALUES[def_lvl]

        # Calculate HP and damage differently if this is an HQ territory
        if is_hq:
            # HQ HP scales with connections and externals
            hp = round(base_hp * (1.5 + 0.25 * (conns + exts)) * (1 + 0.3 * conns))
            # HQ damage scales similarly
            damage = round(damage * (1.5 + 0.25 * (conns + exts)) * (1 + 0.3 * conns))
        else:
            # Non-HQ territories use base HP and damage values
            hp = base_hp
            damage = damage  # explicitly kept for clarity

        # Calculate upper damage bound (1.5x damage)
        damage_high = round(damage * 1.5)

        # Calculate damage per second (DPS) based on damage and attack speed
        dps = round(damage * atk_speed)

        # Calculate effective HP (EHP) accounting for defense percentage
        ehp = round(hp / (1 - def_percent))

        # Build an embed message to display inputs and calculated stats
        embed = discord.Embed(
            title="Territory Defence Calculator",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Inputs",
            value=(
                f"**Conns:** `{conns}` | **Exts:** `{exts}` | **HQ:** `{is_hq}` \n"
                f"**Buffs:** \n- Damage `{dmg_lvl}` \n- Atk Speed `{atk_lvl}` \n- HP `{hp_lvl}` \n- Defence `{def_lvl}`\n"
            ),
            inline=True
        )

        embed.add_field(
            name="Calculated Stats",
            value=(
                f"**HP:** `{hp:,}`\n"
                f"**Damage:** `{damage:,} - {damage_high:,}`\n"
                f"**Defence:** `{int(def_percent * 100)}%`\n"
                f"**Attack Speed:** `{atk_speed:.2f}x`\n\n"
                f"**EHP:** `{int(ehp):,}`\n"
                f"**DPS:** `{dps:,}`"
            ),
            inline=True
        )

        # Send the embed as response to interaction
        await interaction.response.send_message(embed=embed)



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
