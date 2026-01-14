from aiohttp import web
import asyncpg
import bcrypt

from db import row_to_dict
from validators import (
    ValidationError,
    validate_register,
    validate_login,
    validate_create_ad,
    validate_update_ad,
    parse_pagination,
)
from auth import create_jwt


def require_auth(request: web.Request) -> int:
    """
    Возвращает user_id из request['user_id'].
    Если не авторизован — кидает HTTPUnauthorized.
    """
    user_id = request.get("user_id")
    if not user_id:
        raise web.HTTPUnauthorized(reason="Authorization required")
    return int(user_id)


async def register(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_register(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    # Хешируем пароль (bcrypt хранит соль внутри хеша)
    password_hash = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash)
                VALUES ($1, $2)
                RETURNING id, email, created_at;
                """,
                data["email"],
                password_hash,
            )
    except asyncpg.UniqueViolationError:
        return web.json_response({"error": "User already exists"}, status=409)

    return web.json_response(row_to_dict(row), status=201)


async def login(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]
    cfg = request.app["config"]

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_login(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash FROM users WHERE email = $1;",
            data["email"],
        )

    if not user:
        return web.json_response({"error": "Invalid credentials"}, status=401)

    if not bcrypt.checkpw(data["password"].encode("utf-8"), user["password_hash"].encode("utf-8")):
        return web.json_response({"error": "Invalid credentials"}, status=401)

    token = create_jwt(
        user_id=int(user["id"]),
        secret=cfg.JWT_SECRET,
        algorithm=cfg.JWT_ALGORITHM,
        expires_minutes=cfg.JWT_EXPIRES_MINUTES,
    )

    return web.json_response({"token": token})


async def get_all_advertisements(request: web.Request) -> web.Response:
    """
    Список объявлений с пагинацией (защита от переполнения памяти).
    Показываем автора (email).
    """
    pool = request.app["db_pool"]
    limit, offset = parse_pagination(dict(request.query))

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT a.id, a.title, a.description, a.created_at, a.user_id,
                   u.email AS author_email
            FROM advertisements a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.created_at DESC
            LIMIT $1 OFFSET $2;
            """,
            limit,
            offset,
        )

    return web.json_response(
        {
            "items": [row_to_dict(r) for r in rows],
            "limit": limit,
            "offset": offset,
            "count": len(rows),
        }
    )


async def get_advertisement(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]
    ad_id = int(request.match_info["ad_id"])

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.title, a.description, a.created_at, a.user_id,
                   u.email AS author_email
            FROM advertisements a
            JOIN users u ON u.id = a.user_id
            WHERE a.id = $1;
            """,
            ad_id,
        )

    if row is None:
        return web.json_response({"error": "Not found"}, status=404)

    return web.json_response(row_to_dict(row))


async def create_advertisement(request: web.Request) -> web.Response:
    """
    Создание объявления: только авторизованный пользователь.
    user_id берём из токена, а не из тела запроса.
    """
    user_id = require_auth(request)
    pool = request.app["db_pool"]

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_create_ad(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO advertisements (title, description, user_id)
            VALUES ($1, $2, $3)
            RETURNING id, title, description, created_at, user_id;
            """,
            data["title"],
            data["description"],
            user_id,
        )

    return web.json_response(row_to_dict(row), status=201)


async def update_advertisement(request: web.Request) -> web.Response:
    """
    Обновление: только владелец объявления.
    """
    user_id = require_auth(request)
    pool = request.app["db_pool"]
    ad_id = int(request.match_info["ad_id"])

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_update_ad(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    # 1) Сначала проверяем владельца
    async with pool.acquire() as conn:
        owner_row = await conn.fetchrow("SELECT user_id FROM advertisements WHERE id = $1;", ad_id)
        if owner_row is None:
            return web.json_response({"error": "Not found"}, status=404)
        if int(owner_row["user_id"]) != int(user_id):
            return web.json_response({"error": "Forbidden"}, status=403)

        # 2) Делаем обновление
        fields = []
        values = []
        idx = 1
        for k, v in data.items():
            fields.append(f"{k} = ${idx}")
            values.append(v)
            idx += 1
        values.append(ad_id)

        set_clause = ", ".join(fields)

        row = await conn.fetchrow(
            f"""
            UPDATE advertisements
            SET {set_clause}
            WHERE id = ${idx}
            RETURNING id, title, description, created_at, user_id;
            """,
            *values,
        )

    return web.json_response(row_to_dict(row))


async def delete_advertisement(request: web.Request) -> web.Response:
    """
    Удаление: только владелец объявления.
    """
    user_id = require_auth(request)
    pool = request.app["db_pool"]
    ad_id = int(request.match_info["ad_id"])

    async with pool.acquire() as conn:
        owner_row = await conn.fetchrow("SELECT user_id FROM advertisements WHERE id = $1;", ad_id)
        if owner_row is None:
            return web.json_response({"error": "Not found"}, status=404)
        if int(owner_row["user_id"]) != int(user_id):
            return web.json_response({"error": "Forbidden"}, status=403)

        row = await conn.fetchrow("DELETE FROM advertisements WHERE id = $1 RETURNING id;", ad_id)

    return web.json_response({"message": "Deleted", "id": row["id"]})
