import pytest
import yaml

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture()
def raw_config_dict():
    """Raw YAML dict, for tests that mutate the config to prove a guard fires."""
    with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
