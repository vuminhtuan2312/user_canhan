from cryptography.fernet import Fernet

# Key cố định cho module
FERNET_KEY = b'srGltoOLmUuP6YLb6QLojB2ryuyOhEQySRMeyNrQIXE='

_fernet = Fernet(FERNET_KEY)


def encrypt(text: str) -> str:
    if not text:
        return False
    return _fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    if not token:
        return False
    return _fernet.decrypt(token.encode()).decode()
