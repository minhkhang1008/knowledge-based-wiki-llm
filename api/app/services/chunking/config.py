from dataclasses import dataclass


@dataclass
class ChunkConfig:
    chunk_size: int = 500
    overlap: int = 100
    strategy: str = "recursive"
