"""Helpers for loading, saving, and updating YAML configuration and secrets files."""

from pathlib import Path
import yaml

CONFIG_PATH = Path("/config/configuration.yaml")
SECRETS_PATH = Path("/config/secrets.yaml")

def load_yaml(path):
    """Load a YAML file and return its contents as a dictionary.

    Args:
        path (Path or str): Path to the YAML file.

    Returns:
        dict: Parsed YAML data, or empty dict if file is empty.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path, data):
    """Save a dictionary to a YAML file.

    Args:
        path (Path or str): Path to the YAML file.
        data (dict): Data to write to the file.
    """
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

def get_config_value(key):
    """Retrieve a value from the main configuration YAML.

    Args:
        key (str): Key to look up.

    Returns:
        Value for the key, or None if not found.
    """
    config = load_yaml(CONFIG_PATH)
    return config.get(key)

def update_config_value(key, value):
    """Update a value in the main configuration YAML.

    Args:
        key (str): Key to update.
        value: New value to store.
    """
    config = load_yaml(CONFIG_PATH)
    config[key] = value
    save_yaml(CONFIG_PATH, config)

def get_secret_value(key):
    """Retrieve a value from the secrets YAML.

    Args:
        key (str): Key to look up.

    Returns:
        Value for the key, or None if not found.
    """
    secrets = load_yaml(SECRETS_PATH)
    return secrets.get(key)

def update_secret_value(key, value):
    """Update a value in the secrets YAML.

    Args:
        key (str): Key to update.
        value: New value to store.
    """
    secrets = load_yaml(SECRETS_PATH)
    secrets[key] = value
    save_yaml(SECRETS_PATH, secrets)
