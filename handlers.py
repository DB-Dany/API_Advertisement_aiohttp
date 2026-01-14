from aiohttp import web
from validators import ValidationError, validate_create, validate_update, parse_pagination
from db import row_to_dict


async def index(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "service": "Advertisements API",
            "version": "2.0.0",
            "framework": "aiohttp",
            "endpoints": {
                "GET /advertisements": "Get ads (supports ?limit=&offset=)",
                "GET /advertisements/{id}": "Get ad by ID",
                "POST /advertisements": "Create ad",
                "PUT /advertisements/{id}": "Update ad",
                "DELETE /advertisements/{id}": "Delete ad",
                "GET /health": "Health check",
            },
        }
    )


async def health(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1;")
    return web.json_response({"status": "healthy"})


async def get_all_advertisements(request: web.Request) -> web.Response:
    """
    Важно: чтобы не получить OOM, всегда отдаём список постранично.
    """
    pool = request.app["db_pool"]
    limit, offset = parse_pagination(dict(request.query))

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, description, created_at, owner
            FROM advertisements
            ORDER BY created_at DESC
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
            SELECT id, title, description, created_at, owner
            FROM advertisements
            WHERE id = $1;
            """,
            ad_id,
        )

    if row is None:
        return web.json_response({"error": "Not found"}, status=404)

    return web.json_response(row_to_dict(row))


async def create_advertisement(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_create(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO advertisements (title, description, owner)
            VALUES ($1, $2, $3)
            RETURNING id, title, description, created_at, owner;
            """,
            data["title"],
            data["description"],
            data["owner"],
        )

    return web.json_response(row_to_dict(row), status=201)


async def update_advertisement(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]
    ad_id = int(request.match_info["ad_id"])

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        data = validate_update(payload)
    except ValidationError as e:
        return web.json_response({"errors": e.errors}, status=400)

    # Динамическое безопасное обновление через параметры asyncpg ($1, $2, ...)
    fields = []
    values = []
    idx = 1
    for k, v in data.items():
        fields.append(f"{k} = ${idx}")
        values.append(v)
        idx += 1
    values.append(ad_id)  # последний параметр — id

    set_clause = ", ".join(fields)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE advertisements
            SET {set_clause}
            WHERE id = ${idx}
            RETURNING id, title, description, created_at, owner;
            """,
            *values,
        )

    if row is None:
        return web.json_response({"error": "Not found"}, status=404)

    return web.json_response(row_to_dict(row))


async def delete_advertisement(request: web.Request) -> web.Response:
    pool = request.app["db_pool"]
    ad_id = int(request.match_info["ad_id"])

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM advertisements WHERE id = $1 RETURNING id;",
            ad_id,
        )

    if row is None:
        return web.json_response({"error": "Not found"}, status=404)

    return web.json_response({"message": "Deleted", "id": row["id"]})