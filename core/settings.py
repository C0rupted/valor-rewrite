import os, json
from typing import Any, Dict, Literal


# Type alias for valid setting types
SettingType = Literal["number", "boolean", "text", "list"]

# === Define settings schemas for 'user' and 'guild' scopes ===
SETTINGS_SCHEMAS = {
    "user": {
        # Preferred output format for leaderboards (image or text)
        "preferred_leaderboard_output_type": {
            "type": "text", 
            "default": "image", 
            "choices": ["image", "text"], 
            "description": "Preferred output type for leaderboard commands"
        },
        # User interface theme setting
        "theme": {
            "type": "text", 
            "default": "light", 
            "choices": ["light", "dark", "purple"]
        },
    },
    "guild": {
        # Default guild name for commands
        "guild_name": {"type": "text", "default": "",  "description": "Default guild name for commands like /guild and /coolness"},
        # Default guild tag for commands
        "guild_tag": {"type": "text", "default": "",  "description": "Default guild tag for commands like /guild and /coolness"},
    }
}

# Directories where user and guild settings JSON files will be stored
USER_FOLDER = "storages/user_settings"
GUILD_FOLDER = "storages/guild_settings"



class SettingsManager:
    def __init__(self, scope: Literal["user", "guild"], id: int):
        # 'scope' is either "user" or "guild"
        # 'id' is user ID or guild ID as integer
        self.scope = scope
        self.id = str(id)
        self.schema = SETTINGS_SCHEMAS[scope]

        # Filepath for JSON storage depends on scope and ID
        self.path = os.path.join(
            USER_FOLDER if scope == "user" else GUILD_FOLDER,
            f"{self.id}.json"
        )
        # Load settings from disk or use defaults
        self._data = self._load_settings()


    def _load_settings(self) -> Dict[str, Any]:
        # If no file exists yet, create defaults from schema
        if not os.path.exists(self.path):
            return {key: val["default"] for key, val in self.schema.items()}

        try:
            with open(self.path, "r") as f:
                data = json.load(f)
        except Exception:
            # On failure to read JSON (corrupt or inaccessible), use empty dict
            data = {}

        # Make sure all keys exist, else set defaults
        for key, val in self.schema.items():
            if key not in data:
                data[key] = val["default"]
        return data


    def _save_settings(self):
        # Save the internal dict to JSON file with pretty indentation
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=4)


    def get(self, key: str) -> Any:
        # Get value for a given setting key, raises if key invalid
        if key not in self.schema:
            raise KeyError(f"Setting '{key}' does not exist.")
        return self._data.get(key, self.schema[key]["default"])


    def set(self, key: str, value: Any):
        # Validate and set a setting value, then save to disk
        if key not in self.schema:
            raise KeyError(f"Setting '{key}' does not exist.")
        
        schema = self.schema[key]
        expected_type = schema["type"]

        # Validate type (and cast) using _validate_type helper
        validated = self._validate_type(expected_type, value)
        if validated is None:
            raise ValueError(f"Value for '{key}' must be of type '{expected_type}'")

        # Check if value is in allowed choices (if any)
        if "choices" in schema and validated not in schema["choices"]:
            raise ValueError(f"Value for '{key}' must be one of: {schema['choices']}")

        self._data[key] = validated
        self._save_settings()


    def reset(self, key: str):
        # Reset a setting back to its default value
        if key not in self.schema:
            raise KeyError(f"Setting '{key}' does not exist.")
        self._data[key] = self.schema[key]["default"]
        self._save_settings()


    def all(self) -> Dict[str, Any]:
        # Return a copy of all settings currently loaded
        return self._data.copy()


    def _validate_type(self, expected: SettingType, value: Any) -> Any:
        # Validate and cast the value to expected type or return None if invalid
        if expected == "number":
            try:
                return int(value)
            except Exception:
                return None
        if expected == "boolean":
            # Note: bool() on any value always returns True except False, None, 0, ""
            # You may want stricter validation here if needed
            try:
                return bool(value)
            except Exception:
                return None
        if expected == "text":
            try:
                return str(value)
            except Exception:
                return None
        if expected == "list":
            try:
                # Attempt to cast/convert value to list
                return list(value)
            except Exception:
                return None
        return None
