import json

def load_config():
    try:
        with open("admin/config.json", "r", encoding = "utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_config(config):
    with open(f"admin/config.json", "w", encoding = "utf-8") as file:
        json.dump(config, file)

def change_param(param, value):
    config = load_config()
    config[param] = value
    save_config(config)