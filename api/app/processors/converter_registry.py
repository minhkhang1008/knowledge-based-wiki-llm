from typing import Callable, Dict
from pathlib import Path

Converter = Callable[[Path], str]

REGISTRY: Dict[str, Converter] = {}


def register(ext: str):
    def decorator(func: Converter):
        REGISTRY[ext.lower()] = func
        return func
    return decorator


def get_converter(ext: str):
    return REGISTRY.get(ext.lower())
