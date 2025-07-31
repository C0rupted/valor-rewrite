import discord

from discord import app_commands
from discord.ext import commands

from util.embeds import ErrorEmbed
from util.mappings import TERRITORY_DAMAGE_VALUES, TERRITORY_ATTACK_VALUES, TERRITORY_HEALTH_VALUES, TERRITORY_DEFENCE_VALUES



class Utilities(commands.GroupCog, name="utilities"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="calculate_territory_defences", description="Calculate tower stats based on buffs and HQ status.")
    @app_commands.describe(
        buffs="Four upgrade levels separated by commas (e.g. 4,8,2,11 or 4x11)",
        conns="Number of connections (default 0)",
        exts="Number of externals (default 0)",
        is_hq="Is this an HQ territory? (default True)"
    )
    async def calculate_territory_defences(self, interaction: discord.Interaction, conns: int = 0, exts: int = 0, buffs: str = "4x11", is_hq: bool = True):
        try:
            if buffs.strip().startswith("4x"):
                parts = buffs.split("x")
                if len(parts) != 2:
                    raise ValueError()
                buffs_list = [int(parts[1])] * 4
            else:
                buffs_list = list(map(int, buffs.split(",")))
                if len(buffs_list) != 4:
                    raise ValueError()
        except Exception:
            return await interaction.response.send_message(embed=ErrorEmbed("Please use either `4x11` or `4,8,2,11` format."), ephemeral=True)

        dmg_lvl, atk_lvl, hp_lvl, def_lvl = buffs_list

        # Clamp to 0–11
        if not all(0 <= b <= 11 for b in buffs_list):
            return await interaction.response.send_message(embed=ErrorEmbed("Each buff level must be between 0 and 11."), ephemeral=True)

        damage = TERRITORY_DAMAGE_VALUES[dmg_lvl]
        atk_speed = TERRITORY_ATTACK_VALUES[atk_lvl]
        base_hp = TERRITORY_HEALTH_VALUES[hp_lvl]
        def_percent = TERRITORY_DEFENCE_VALUES[def_lvl]

        if is_hq:
            hp = round(base_hp * (1.5 + 0.25 * (conns + exts)) * (1 + 0.3 * conns))
            damage = round(damage * (1.5 + 0.25 * (conns + exts)) * (1 + 0.3 * conns))
        else:
            hp = base_hp
            damage = damage

        damage_high = round(damage * 1.5)
        dps = round(damage * atk_speed)
        ehp = round(hp / (1 - def_percent))

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

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
