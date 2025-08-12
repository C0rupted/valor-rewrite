import discord, logging

from discord import app_commands
from discord.app_commands import Choice, checks
from discord.ext import commands

from core.settings import SettingsManager, SETTINGS_SCHEMAS
from util.embeds import ErrorEmbed, InfoEmbed


class ValueModal(discord.ui.Modal, title="Set Setting Value"):
    """
    Modal UI to allow the user to input a new value for a setting.
    Handles both simple values and list additions/removals.
    """

    def __init__(
        self,
        user: discord.User,
        manager: SettingsManager,
        key: str,
        target_id: int,
        scope: str,
        interaction: discord.Interaction,
        field_label: str = "Value",
        is_list: bool = False,
        list_add_or_remove: str = None,
    ):
        """
        Initialize the modal.

        Args:
            user: The user who invoked the modal (only this user can interact).
            manager: SettingsManager instance managing the setting.
            key: The setting key being edited.
            target_id: Target ID (user or guild ID depending on scope).
            scope: Scope of the setting ("user" or "guild").
            interaction: Original interaction that invoked this modal.
            field_label: Label for the text input.
            is_list: Whether the setting is a list type.
            list_add_or_remove: If list, indicates "add" or "remove" operation.
        """
        super().__init__()
        self.user = user
        self.manager = manager
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.is_list = is_list
        self.list_add_or_remove = list_add_or_remove
        # Single text input field for value entry
        self.input = discord.ui.TextInput(label=field_label, placeholder="Enter a value")
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        """
        Called when the modal is submitted.

        Processes the input value, updates the setting, and edits the original message.
        """
        # Only allow the user who opened the modal to interact
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't interact with this modal.", ephemeral=True
            )

        try:
            if self.is_list:
                # For list type settings, modify the list accordingly
                l = self.manager.get(self.key)
                if self.list_add_or_remove == "remove":
                    l.remove(self.input.value)
                else:
                    l.append(self.input.value)
                self.manager.set(self.key, l)
            else:
                # For single values, just set the value directly
                self.manager.set(self.key, self.input.value)

            # After setting value, rebuild the embed and update the original message
            updated_embed = await construct_embed(self.key, self.target_id, self.scope)
            await self.original_interaction.edit_original_response(
                embed=updated_embed,
                view=SettingsView(self.original_interaction, self.key, self.scope),
            )

            # Confirm to the user that the setting was updated
            await interaction.response.send_message("Setting updated.", ephemeral=True)
        except ValueError as e:
            # Handle errors, e.g. removing a value not in the list
            if self.is_list:
                embed = ErrorEmbed(f"Value '{self.input.value}' is not found in the list")
            else:
                embed = ErrorEmbed(str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)



class ChoiceDropdown(discord.ui.Select):
    """
    Dropdown select UI element for settings that have predefined choices.
    Allows user to pick from a list of valid options.
    """

    def __init__(
        self,
        user: discord.User,
        manager: SettingsManager,
        key: str,
        target_id: int,
        scope: str,
        choices: list[str],
        interaction: discord.Interaction,
    ):
        """
        Initialize the dropdown menu with the given choices.

        Args:
            user: User who can interact with this dropdown.
            manager: SettingsManager instance for the setting.
            key: Setting key.
            target_id: Target ID (user or guild).
            scope: Scope of the setting.
            choices: List of valid choices for the setting.
            interaction: The original interaction.
        """
        self.user = user
        self.manager = manager
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction

        # Convert string choices into Discord SelectOption objects
        options = [discord.SelectOption(label=val, value=val) for val in choices]
        super().__init__(
            placeholder="Choose a value", options=options, min_values=1, max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        """
        Called when the user selects a value from the dropdown.
        Updates the setting accordingly and updates the original message.
        """
        # Only allow the user who opened the dropdown to interact
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't interact with this menu.", ephemeral=True
            )

        try:
            # Set the selected value in the manager
            self.manager.set(self.key, self.values[0])

            # Update the original message with new embed and view
            updated_embed = await construct_embed(self.key, self.target_id, self.scope)
            await self.original_interaction.edit_original_response(
                embed=updated_embed,
                view=SettingsView(self.original_interaction, self.key, self.scope),
            )

            # Acknowledge the interaction with a brief info message and remove the dropdown view
            await interaction.response.edit_message(embed=InfoEmbed("Setting updated."), view=None)
        except ValueError as e:
            # Send error embed on failure
            await interaction.response.send_message(embed=ErrorEmbed(str(e)), ephemeral=True)



class ChoiceView(discord.ui.View):
    """
    View containing the dropdown for selecting a choice from predefined options.
    """

    def __init__(
        self,
        user: discord.User,
        key: str,
        target_id: int,
        scope: str,
        interaction: discord.Interaction,
    ):
        """
        Initialize the view and add the ChoiceDropdown item.

        Args:
            user: The user allowed to interact.
            key: Setting key.
            target_id: Target ID.
            scope: Scope ("user" or "guild").
            interaction: The original interaction.
        """
        super().__init__(timeout=60)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        # Initialize a SettingsManager instance for the current scope and target
        self.manager = SettingsManager(self.scope, target_id)
        # Retrieve the setting schema to get available choices
        schema = SETTINGS_SCHEMAS[self.scope][key]

        # Add a dropdown select to the view with all the choices
        self.add_item(
            ChoiceDropdown(
                self.user,
                SettingsManager(self.scope, self.target_id),
                self.key,
                self.target_id,
                self.scope,
                schema["choices"],
                interaction,
            )
        )



class ConfirmResetView(discord.ui.View):
    """
    Confirmation dialog view with "Confirm" and "Cancel" buttons for resetting a setting.
    """

    def __init__(
        self,
        user: discord.User,
        manager: SettingsManager,
        key: str,
        target_id: int,
        scope: str,
        original_interaction: discord.Interaction,
    ):
        """
        Initialize the view.

        Args:
            user: User allowed to confirm/cancel.
            manager: SettingsManager instance.
            key: Setting key.
            target_id: Target ID.
            scope: Scope.
            original_interaction: Interaction to edit on confirmation.
        """
        super().__init__(timeout=30)
        self.user = user
        self.manager = manager
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = original_interaction

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Reset the setting to default and update the original message.
        """
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't interact with this.", ephemeral=True
            )

        # Reset the setting to its default value
        self.manager.reset(self.key)
        # Rebuild embed and update original message
        updated_embed = await construct_embed(self.key, self.target_id, self.scope)
        await self.original_interaction.edit_original_response(
            embed=updated_embed, view=SettingsView(self.original_interaction, self.key, self.scope)
        )
        # Edit the confirmation message with success info and remove buttons
        await interaction.response.edit_message(
            embed=InfoEmbed("Setting reset to default."), view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel the reset operation and close the confirmation view.
        """
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't interact with this.", ephemeral=True
            )

        # Acknowledge cancellation and remove the confirmation view
        await interaction.response.edit_message(embed=InfoEmbed("Reset cancelled."), view=None)



class SettingsView(discord.ui.View):
    """
    Main settings view containing buttons for setting, toggling, adding/removing list values, and resetting.
    The buttons shown depend on the setting type.
    """

    def __init__(self, interaction: discord.Interaction, key: str, scope: str):
        """
        Initialize the view and add the appropriate buttons based on setting type.

        Args:
            interaction: The original interaction.
            key: Setting key.
            scope: Setting scope ("user" or "guild").
        """
        super().__init__(timeout=60)
        self.user = interaction.user
        self.key = key
        # Determine target ID based on scope: user ID or guild ID
        self.target_id = interaction.guild.id if scope == "guild" else interaction.user.id
        self.scope = scope
        self.manager = SettingsManager(self.scope, self.target_id)
        self.interaction = interaction
        # Retrieve setting schema for type and choices
        schema = SETTINGS_SCHEMAS[self.scope][key]

        type_ = schema["type"]

        # Add buttons based on setting type
        if type_ in ["text", "number"]:
            self.add_item(SetButton(self.user, key, self.target_id, scope, interaction, self.manager))
        elif type_ == "bool":
            self.add_item(BoolButton(self.user, key, self.target_id, scope, interaction, self.manager))
        elif type_ == "list":
            self.add_item(AddButton(self.user, key, self.target_id, scope, interaction, self.manager))
            self.add_item(RemoveButton(self.user, key, self.target_id, scope, interaction, self.manager))

        # Always add a reset button
        self.add_item(ResetButton(self.user, key, self.target_id, scope, interaction, self.manager))



class SetButton(discord.ui.Button):
    """
    Button to set a new value for a text or number setting.
    """

    def __init__(self, user, key, target_id, scope, interaction, manager):
        """
        Initialize the SetButton.

        Args:
            user: User allowed to press the button.
            key: Setting key.
            target_id: Target ID.
            scope: Setting scope.
            interaction: Original interaction.
            manager: SettingsManager instance.
        """
        super().__init__(label="Set Value", style=discord.ButtonStyle.primary)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.manager = manager

    async def callback(self, interaction: discord.Interaction):
        """
        Show either a dropdown or a modal for the user to set a new value.
        """
        # Only the original user can press this button
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "Only the command user can press this button.", ephemeral=True
            )

        schema = SETTINGS_SCHEMAS[self.scope][self.key]
        # If there are predefined choices, show a dropdown view
        if "choices" in schema:
            await interaction.response.send_message(
                view=ChoiceView(
                    self.user, self.key, self.target_id, self.scope, self.original_interaction
                ),
                ephemeral=True,
            )
        else:
            # Otherwise, show a modal text input for free-form input
            await interaction.response.send_modal(
                ValueModal(
                    self.user, self.manager, self.key, self.target_id, self.scope, self.original_interaction
                )
            )



class BoolButton(discord.ui.Button):
    """
    Button to toggle a boolean setting on/off.
    """

    def __init__(self, user, key, target_id, scope, interaction, manager):
        """
        Initialize the BoolButton.

        Args:
            user: User allowed to press the button.
            key: Setting key.
            target_id: Target ID.
            scope: Setting scope.
            interaction: Original interaction.
            manager: SettingsManager instance.
        """
        super().__init__(label="Toggle Setting", style=discord.ButtonStyle.primary)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.manager = manager

    async def callback(self, interaction: discord.Interaction):
        """
        Toggle the boolean setting and update the original message.
        """
        # Only the original user can press this button
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "Only the command user can press this button.", ephemeral=True
            )

        # Toggle the boolean value by negating current
        b = not self.manager.get(self.key)
        self.manager.set(self.key, b)

        # Update the embed and view on the original interaction message
        updated_embed = await construct_embed(self.key, self.target_id, self.scope)
        await self.original_interaction.edit_original_response(
            embed=updated_embed, view=SettingsView(self.original_interaction, self.key, self.scope)
        )

        # Confirm the update to the user
        await interaction.response.send_message("Setting updated.", ephemeral=True)



class AddButton(discord.ui.Button):
    """
    Button to add a value to a list setting.
    """

    def __init__(self, user, key, target_id, scope, interaction, manager):
        """
        Initialize the AddButton.

        Args:
            user: User allowed to press.
            key: Setting key.
            target_id: Target ID.
            scope: Setting scope.
            interaction: Original interaction.
            manager: SettingsManager instance.
        """
        super().__init__(label="Add Value", style=discord.ButtonStyle.success)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.manager = manager

    async def callback(self, interaction: discord.Interaction):
        """
        Show a modal to enter a value to add to the list.
        """
        # Only original user allowed
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "Only the command user can press this button.", ephemeral=True
            )
        await interaction.response.send_modal(
            ValueModal(
                self.user,
                self.manager,
                self.key,
                self.target_id,
                self.scope,
                self.original_interaction,
                field_label="Value to add",
                is_list=True,
            )
        )



class RemoveButton(discord.ui.Button):
    """
    Button to remove a value from a list setting.
    """

    def __init__(self, user, key, target_id, scope, interaction, manager):
        """
        Initialize the RemoveButton.

        Args:
            user: User allowed to press.
            key: Setting key.
            target_id: Target ID.
            scope: Setting scope.
            interaction: Original interaction.
            manager: SettingsManager instance.
        """
        super().__init__(label="Remove Value", style=discord.ButtonStyle.danger)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.manager = manager

    async def callback(self, interaction: discord.Interaction):
        """
        Show a modal to enter a value to remove from the list.
        """
        # Only original user allowed
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "Only the command user can press this button.", ephemeral=True
            )
        await interaction.response.send_modal(
            ValueModal(
                self.user,
                self.manager,
                self.key,
                self.target_id,
                self.scope,
                self.original_interaction,
                field_label="Value to remove",
                is_list=True,
                list_add_or_remove="remove",
            )
        )



class ResetButton(discord.ui.Button):
    """
    Button to reset a setting to its default value, with confirmation.
    """

    def __init__(self, user, key, target_id, scope, interaction, manager):
        """
        Initialize the ResetButton.

        Args:
            user: User allowed to press.
            key: Setting key.
            target_id: Target ID.
            scope: Setting scope.
            interaction: Original interaction.
            manager: SettingsManager instance.
        """
        super().__init__(label="Reset to Default", style=discord.ButtonStyle.secondary)
        self.user = user
        self.key = key
        self.target_id = target_id
        self.scope = scope
        self.original_interaction = interaction
        self.manager = manager

    async def callback(self, interaction: discord.Interaction):
        """
        Prompt the user to confirm resetting the setting to its default.
        """
        # Only original user allowed
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "Only the command user can press this button.", ephemeral=True
            )

        # Send ephemeral message with confirmation view
        await interaction.response.send_message(
            embed=InfoEmbed("Are you sure you want to reset this setting to default?"),
            view=ConfirmResetView(
                self.user, self.manager, self.key, self.target_id, self.scope, self.original_interaction
            ),
            ephemeral=True,
        )



async def construct_embed(key: str, user_id: str, scope: str) -> discord.Embed:
    """
    Construct an embed displaying setting information: type, current value, default, and choices if applicable.

    Args:
        key: Setting key.
        user_id: ID of the user or guild the setting applies to.
        scope: Scope of the setting ("user" or "guild").

    Returns:
        A discord.Embed instance representing the setting info.
    """
    schema = SETTINGS_SCHEMAS[scope][key]
    manager = SettingsManager(scope, user_id)
    current = manager.get(key)

    # Human-friendly label for the setting
    key_label = key.replace("_", " ").capitalize()
    embed = discord.Embed(
        title=f"{scope.capitalize()} Setting: {key_label}",
        description=schema.get("description", ""),
    )

    embed.add_field(name="Type", value=schema["type"].capitalize(), inline=True)

    # If setting has predefined choices, list them
    if "choices" in schema:
        embed.add_field(name="Choices", value=", ".join(map(str, schema["choices"])), inline=True)

    # Current value and default value (capitalize, remove quotes for readability)
    embed.add_field(
        name="Current Value",
        value=(str(current).replace("'", "") if current else "None"),
        inline=False,
    )
    embed.add_field(
        name="Default Value",
        value=(str(schema.get("default")).replace("'", "").capitalize() if schema.get("default") else "None"),
        inline=False,
    )

    return embed



class SettingsCommands(commands.Cog):
    """
    Cog providing commands to view and edit user or guild settings.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="user_settings", description="View and edit your user settings")
    @app_commands.describe(setting="The setting you want to manage")
    async def user_settings(self, interaction: discord.Interaction, setting: str):
        """
        Slash command to view and edit a user setting.

        Args:
            interaction: The interaction object.
            setting: The setting key to manage.
        """
        schema = SETTINGS_SCHEMAS["user"].get(setting)
        if not schema:
            return await interaction.response.send_message("Invalid setting selected.", ephemeral=True)

        embed = await construct_embed(setting, interaction.user.id, "user")
        await interaction.response.send_message(
            embed=embed,
            view=SettingsView(interaction, setting, "user"),
        )


    @app_commands.command(name="guild_settings", description="View and edit this server's settings")
    @checks.has_permissions(administrator=True)
    @app_commands.describe(setting="The setting you want to manage")
    async def guild_settings(self, interaction: discord.Interaction, setting: str):
        """
        Slash command to view and edit a guild setting.

        Args:
            interaction: The interaction object.
            setting: The setting key to manage.
        """
        schema = SETTINGS_SCHEMAS["guild"].get(setting)
        if not schema:
            return await interaction.response.send_message("Invalid setting selected.", ephemeral=True)

        embed = await construct_embed(setting, interaction.guild.id, "guild")
        await interaction.response.send_message(
            embed=embed,
            view=SettingsView(interaction, setting, "guild"),
        )


    @user_settings.autocomplete("setting")
    async def user_settings_autocomplete(self, interaction: discord.Interaction, current: str) -> list[Choice[str]]:
        """
        Autocomplete handler for user settings command.

        Args:
            interaction: The interaction object.
            current: Current input string.

        Returns:
            List of Choices matching available user settings.
        """
        autocomplete = []
        for setting in SETTINGS_SCHEMAS["user"].keys():
            name = setting.replace("_", " ").capitalize()
            autocomplete.append(Choice(name=name, value=setting))
        return autocomplete


    @guild_settings.autocomplete("setting")
    async def guild_settings_autocomplete(self, interaction: discord.Interaction, current: str) -> list[Choice[str]]:
        """
        Autocomplete handler for guild settings command.

        Args:
            interaction: The interaction object.
            current: Current input string.

        Returns:
            List of Choices matching available guild settings.
        """
        autocomplete = []
        for setting in SETTINGS_SCHEMAS["guild"].keys():
            name = setting.replace("_", " ").capitalize()
            autocomplete.append(Choice(name=name, value=setting))
        return autocomplete



# Cog setup function for bot
async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCommands(bot))
