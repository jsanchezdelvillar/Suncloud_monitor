import yaml
from pathlib import Path

CONFIG_PATH = Path("/config/configuration.yaml")
SECRETS_PATH = Path("/config/secrets.yaml")

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f)

def get_config_value(key):
    config = load_yaml(CONFIG_PATH)
    return config.get(key)

def update_config_value(key, value):
    config = load_yaml(CONFIG_PATH)
    config[key] = value
    save_yaml(CONFIG_PATH, config)

def get_secret_value(key):
    secrets = load_yaml(SECRETS_PATH)
    return secrets.get(key)

def update_secret_value(key, value):
    secrets = load_yaml(SECRETS_PATH)
    secrets[key] = value
    save_yaml(SECRETS_PATH, secrets)
