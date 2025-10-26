import string

# Base62 alphabet
ALPHABET = string.digits + string.ascii_letters  # 0-9A-Za-z
BASE = len(ALPHABET)

def encode_ref_id(num: int) -> str:
    """Encode integer telegram_id to short base62 string."""
    if num == 0:
        return ALPHABET[0]
    encoded = ""
    while num > 0:
        num, rem = divmod(num, BASE)
        encoded = ALPHABET[rem] + encoded
    return encoded

def decode_ref_id(code: str) -> int:
    """Decode base62 string back to integer."""
    num = 0
    for char in code:
        num = num * BASE + ALPHABET.index(char)
    return num
