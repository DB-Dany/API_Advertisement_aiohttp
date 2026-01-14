import time
from typing import Optional, Dict, Any

import jwt


def create_jwt(*, user_id: int, secret: str, algorithm: str, expires_minutes: int) -> str:
    """
    Создаём JWT токен. В payload кладём user_id и время истечения exp.
    """
    now = int(time.time())
    payload = {
        "sub": str(user_id),          # стандартное поле "subject"
        "iat": now,                   # issued at
        "exp": now + expires_minutes * 60,
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    # PyJWT может вернуть bytes в некоторых версиях — нормализуем в str
    return token.decode("utf-8") if isinstance(token, bytes) else token


def decode_jwt(token: str, *, secret: str, algorithm: str) -> Dict[str, Any]:
    """
    Декодируем токен. Если токен просрочен/битый — будет исключение.
    """
    return jwt.decode(token, secret, algorithms=[algorithm])


def extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    """
    Достаём Bearer токен из заголовка Authorization: Bearer <token>
    """
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]
