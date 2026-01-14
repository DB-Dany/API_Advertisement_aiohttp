import logging
from aiohttp import web
import jwt

from config import Config
from db import create_pool, init_db
from auth import extract_bearer_token, decode_jwt
from handlers import (
    register,
    login,
    get_all_advertisements,
    get_advertisement,
    create_advertisement,
    update_advertisement,
    delete_advertisement,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@web.middleware
async def error_middleware(request: web.Request, handler):
    """
    Единый middleware для обработки ошибок. Всегда возвращаем JSON.
    """
    try:
        return await handler(request)
    except web.HTTPException as e:
        return web.json_response({"error": e.reason}, status=e.status)
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
        return web.json_response({"error": "Internal server error"}, status=500)


@web.middleware
async def auth_middleware(request: web.Request, handler):
    """
    Middleware аутентификации:
    - если есть Authorization: Bearer <token>, пытаемся декодировать JWT
    - если токен валиден — кладём user_id в request["user_id"]
    - если токен неверный/просрочен — 401
    """
    cfg: Config = request.app["config"]
    token = extract_bearer_token(request.headers.get("Authorization"))

    if token:
        try:
            payload = decode_jwt(token, secret=cfg.JWT_SECRET, algorithm=cfg.JWT_ALGORITHM)
            request["user_id"] = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return web.json_response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return web.json_response({"error": "Invalid token"}, status=401)

    return await handler(request)


async def on_startup(app: web.Application):
    cfg: Config = app["config"]
    app["db_pool"] = await create_pool(cfg)
    await init_db(app["db_pool"])
    logger.info("Database pool created and tables ensured.")


async def on_cleanup(app: web.Application):
    pool = app.get("db_pool")
    if pool is not None:
        await pool.close()
        logger.info("Database pool closed.")


def create_app() -> web.Application:
    app = web.Application(middlewares=[error_middleware, auth_middleware])
    app["config"] = Config()

    # Auth
    app.router.add_post("/register", register)
    app.router.add_post("/login", login)

    # Ads CRUD
    app.router.add_get("/advertisements", get_all_advertisements)
    app.router.add_post("/advertisements", create_advertisement)
    app.router.add_get(r"/advertisements/{ad_id:\d+}", get_advertisement)
    app.router.add_put(r"/advertisements/{ad_id:\d+}", update_advertisement)
    app.router.add_delete(r"/advertisements/{ad_id:\d+}", delete_advertisement)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    cfg = Config()
    web.run_app(create_app(), host=cfg.APP_HOST, port=cfg.APP_PORT)
