from pathlib import Path
from typing import Union

import yaml
from yaml import Loader
from collections.abc import Iterable


def read_yaml(
    file: Union[str, Path], key: str = None, default: Union[str, dict] = None
) -> dict:
    """
    Read yaml file and return `dict`.

    Args:
        file: `str` or `Path`. Yaml file path.
        key: `str`. Yaml key you want to read.
        default: `str` or `dict`. Yaml key or default dict to use as default values.

    Returns:
        Yaml file content as `dict` object.
    """
    with open(file, "r") as fp:
        params = yaml.load(fp, Loader)
    default = (
        default
        if isinstance(default, dict)
        else (params[default] if isinstance(default, str) else dict())
    )
    result = params[key] if key else params
    return {**default, **result}


def dump_yaml(
    obj: dict, file_path: Union[str, Path], key: str = None, norm: bool = True
) -> Path:
    """
    Write yaml file and return `Path`.

    Args:
        obj: `dict` to write to yaml file.
        file: `str` or `Path`. Yaml file path.
        key: `str`. dict key you want to write.
        norm: `bool`. flag to normalize float values or not.

    Returns:
        `Path` of yaml file after writing.
    """
    obj = obj[key] if key else obj
    if norm:
        obj = normalize(obj)
    with open(file_path, "w+") as file:
        yaml.dump(obj, file)
    return Path(file_path)


def normalize(obj: dict, ndigits: int = 4) -> dict:
    """Normalizes float values to `ndigits` decimal places"""
    if isinstance(obj, (float,)):
        return round(obj, ndigits)
    if isinstance(obj, (str,)):
        return obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = normalize(value, ndigits)
        return obj
    if isinstance(obj, Iterable):
        return [normalize(x, ndigits) for x in obj]
    return obj
