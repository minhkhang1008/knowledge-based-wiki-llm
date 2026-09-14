from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Shared ingestion limits, expressed in estimated tokens."""

    chunk_size: int = 400
    overlap: int = 50
    min_chunk_size: int = 80
    image_chunk_size: int = 300
    image_overlap: int = 30
    strategy: str = "structure_aware"

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0")
        if self.overlap < 0 or self.overlap >= self.chunk_size:
            raise ValueError("overlap phải từ 0 đến nhỏ hơn chunk_size")
        if self.min_chunk_size < 0:
            raise ValueError("min_chunk_size không được âm")
        if self.image_chunk_size <= 0:
            raise ValueError("image_chunk_size phải lớn hơn 0")
        if self.image_overlap < 0 or self.image_overlap >= self.image_chunk_size:
            raise ValueError("image_overlap phải từ 0 đến nhỏ hơn image_chunk_size")
