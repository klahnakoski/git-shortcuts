from mo_files import File
from mo_json import value2json

ALIAS_FILE = ".git/hit-aliases.json"


def load_aliases():
    try:
        return File(ALIAS_FILE).read_json()
    except Exception as cause:
        return {}


def save_alias(alias_map):
    File(ALIAS_FILE).write(value2json(alias_map, pretty=True))


def add_alias(long_name, alias):
    alias_map = load_aliases()
    alias_map[alias] = long_name
    save_alias(alias_map)
