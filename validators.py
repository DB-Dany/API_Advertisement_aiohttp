from typing import Any, Dict, Tuple
import re


class ValidationError(Exception):
    def __init__(self, errors: Dict[str, str]):
        super().__init__("Validation error")
        self.errors = errors


def _not_empty(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_register(payload: Dict[str, Any]) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    email = payload.get("email")
    password = payload.get("password")

    if not _not_empty(email) or not EMAIL_RE.match(email.strip()):
        errors["email"] = "Invalid email"

    if not _not_empty(password) or len(password.strip()) < 6:
        errors["password"] = "Password must be at least 6 characters"

    if errors:
        raise ValidationError(errors)

    return {"email": email.strip().lower(), "password": password}


def validate_login(payload: Dict[str, Any]) -> Dict[str, str]:
    # По сути та же валидация, что и register
    return validate_register(payload)


def validate_create_ad(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: Dict[str, str] = {}

    title = payload.get("title")
    description = payload.get("description")

    if not _not_empty(title):
        errors["title"] = "Field cannot be empty"
    elif len(title.strip()) > 200:
        errors["title"] = "Max length is 200"

    if not _not_empty(description):
        errors["description"] = "Field cannot be empty"

    if errors:
        raise ValidationError(errors)

    return {"title": title.strip(), "description": description.strip()}


def validate_update_ad(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"title", "description"}
    data = {k: v for k, v in payload.items() if k in allowed}

    if not data:
        raise ValidationError({"_": "No fields to update"})

    errors: Dict[str, str] = {}
    out: Dict[str, Any] = {}

    if "title" in data:
        v = data["title"]
        if v is None or not _not_empty(v):
            errors["title"] = "Field cannot be empty"
        else:
            v = v.strip()
            if len(v) > 200:
                errors["title"] = "Max length is 200"
            else:
                out["title"] = v

    if "description" in data:
        v = data["description"]
        if v is None or not _not_empty(v):
            errors["description"] = "Field cannot be empty"
        else:
            out["description"] = v.strip()

    if errors:
        raise ValidationError(errors)

    return out


def parse_pagination(query: Dict[str, str]) -> tuple[int, int]:
    # Защита от OOM: ограничиваем limit
    limit_default = 50
    limit_max = 200
