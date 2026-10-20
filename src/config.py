"""load sources.yml"""
import os
import yaml


def load_config(repo_root: str) -> dict:
    with open(os.path.join(repo_root, "sources.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)
