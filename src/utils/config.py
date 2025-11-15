import yaml

import yaml

import yaml

def load_config(config_path: str):
    """Load configuration from a YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)




