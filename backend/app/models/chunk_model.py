from dataclasses import dataclass
from typing import Dict

@dataclass
class Chunk:
    id: str
    content: str
    metadata: Dict