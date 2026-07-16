from typing import Callable, Dict
from pathlib import Path

Converter = Callable[[Path, str], str]

REGISTRY: Dict[str, Converter] = {}

def register(ext: str):
    """Decorator để đăng ký một converter cho một định dạng file cụ thể."""
    def decorator(func: Converter):
        REGISTRY[ext.lower()] = func
        return func
    return decorator

def get_converter(ext: str) -> Converter | None:
    return REGISTRY.get(ext.lower())