import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def cipher():
    key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY')
    if not key:
        path = Path(settings.BASE_DIR) / '.credential-key'
        try:
            with path.open('xb') as file:
                file.write(Fernet.generate_key())
        except FileExistsError:
            pass
        key = path.read_bytes()
    return Fernet(key)


def encrypt(password):
    return cipher().encrypt(password.encode()).decode()


def recover(user):
    if not user.issued_password:
        return ''
    try:
        password = cipher().decrypt(user.issued_password.encode()).decode()
    except InvalidToken:
        return ''
    return password if user.check_password(password) else ''
