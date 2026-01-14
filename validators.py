from typing import Any, Dict


class ValidationError(Exception):
    """Ошибка валидации входных данных."""
    def __init__(self, errors: Dict[str, str]):
        super().__init__("Validation error")
        self.errors = errors


def _not_empty(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидация создания объявления.
    Требуются поля: title, description, owner.
    """
    errors: Dict[str, str] = {}

    title = payload.get("title")
    description = payload.get("description")
    owner = payload.get("owner")

    if not _not_empty(title):
        errors["title"] = "Field cannot be empty"
    elif len(title.strip()) > 200:
        errors["title"] = "Max length is 200"

    if not _not_empty(description):
        errors["description"] = "Field cannot be empty"

    if not _not_empty(owner):
        errors["owner"] = "Field cannot be empty"
    elif len(owner.strip()) > 100:
        errors["owner"] = "Max length is 100"

    if errors:
        raise ValidationError(errors)

    return {
        "title": title.strip(),
        "description": description.strip(),
        "owner": owner.strip(),
    }


def validate_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидация обновления объявления (частичное обновление).
    Разрешены поля: title, description, owner.
    Хотя бы одно поле должно присутствовать.
    """
    allowed = {"title", "description", "owner"}
    data = {k: v for k, v in payload.items() if k in allowed}

    if not data:
        raise ValidationError({"_": "No fields to update"})

    errors: Dict[str, str] = {}
    out: Dict[str, Any] = {}

    if "title" in data:
        v = data["title"]
        if v is None:
            pass
        elif not _not_empty(v):
            errors["title"] = "Field cannot be empty"
        else:
            v = v.strip()
            if len(v) > 200:
                errors["title"] = "Max length is 200"
            else:
                out["title"] = v

    if "description" in data:
        v = data["description"]
        if v is None:
            pass
        elif not _not_empty(v):
            errors["description"] = "Field cannot be empty"
        else:
            out["description"] = v.strip()

    if "owner" in data:
        v = data["owner"]
        if v is None:
            pass
        elif not _not_empty(v):
            errors["owner"] = "Field cannot be empty"
        else:
            v = v.strip()
            if len(v) > 100:
                errors["owner"] = "Max length is 100"
            else:
                out["owner"] = v

    if errors:
        raise ValidationError(errors)

    if not out:
        raise ValidationError({"_": "No valid fields to update"})

    return out


def parse_pagination(query: Dict[str, str]) -> tuple[int, int]:
    """
    Защита от переполнения памяти:
    - limit по умолчанию 50, максимум 200
    - offset по умолчанию 0
    """
    limit_default = 50
    limit_max = 200

    def to_int(value: str | None, default: int) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    limit = to_int(query.get("limit"), limit_default)
    offset = to_int(query.get("offset"), 0)

    if limit < 1:
        limit = limit_default
    if limit > limit_max:
        limit = limit_max
    if offset < 0:
        offset = 0

    return limit, offset