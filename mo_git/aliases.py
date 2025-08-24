import json
import os

ALIAS_FILE = ".git/hit-aliases.json"


def load_aliases():
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE) as f:
            return json.load(f)
    return {}


def save_alias(alias_map):
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)
    with open(ALIAS_FILE, "w") as f:
        json.dump(alias_map, f, indent=2)


def add_alias(long_name, alias):
    alias_map = load_aliases()
    alias_map[long_name] = alias
    save_alias(alias_map)
    print(f"Alias '{alias}' added for '{long_name}'")
