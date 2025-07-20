import yaml

def load_cfg(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
