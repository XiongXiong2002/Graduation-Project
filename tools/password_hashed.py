from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def verify_legal_password(password: str) -> bool:
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_special = any(not c.isalnum() for c in password)
    long_enough = len(password) >= 8
    short_enough = len(password) <= 20
    return has_lower and has_upper and has_special and long_enough and short_enough