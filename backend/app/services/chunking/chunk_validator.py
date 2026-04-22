
from .config import MIN_CHUNK_SIZE, MAX_CHUNK_SIZE

def validate_chunk(chunk):
    length = len(chunk.content)

    if length < MIN_CHUNK_SIZE:
        return False
    
    if length > MAX_CHUNK_SIZE:
        return False
    

    return True