import logging
from aiohttp import web

from config import Config
from db import create_pool, init_db
from handlers import (
    index,
    health,
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
    Единый middleware для обработки ошибок.
    Всегда возвращает JSON-ответ.
    """
    try:
        return await handler(request)
    except web.HTTPException as e:
        return web.json_response(
            {"error": e.reason},
            status=e.status,
        )
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
        return web.json_response(
            {"error": "Internal server error"},
            status=500,
        )


async def on_startup(app: web.Application):
    """
    Инициализация при запуске приложения:
    - создание пула соединений с БД
    - создание таблиц (если их ещё нет)
    """
    cfg: Config = app["config"]
    app["db_pool"] = await create_pool(cfg)
    await init_db(app["db_pool"])
    logger.info("Database pool created and tables ensured.")


async def on_cleanup(app: web.Application):
    """
    Корректное закрытие ресурсов при остановке приложения
    """
    pool = app.get("db_pool")
    if pool is not None:
        await pool.close()
        logger.info("Database pool closed.")


def create_app() -> web.Application:
    app = web.Application(middlewares=[error_middleware])

    # Конфигурация приложения
    app["config"] = Config()

    # Служебные маршруты
    app.router.add_get("/", index)
    app.router.add_get("/health", health)

    # CRUD маршруты для объявлений
    app.router.add_get("/advertisements", get_all_advertisements)
    app.router.add_post("/advertisements", create_advertisement)

    # ⚠️ Используем raw-строки (r"...") для regex \d+
    app.router.add_get(r"/advertisements/{ad_id:\d+}", get_advertisement)
    app.router.add_put(r"/advertisements/{ad_id:\d+}", update_advertisement)
    app.router.add_delete(r"/advertisements/{ad_id:\d+}", delete_advertisement)

    # Хуки жизненного цикла
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


if __name__ == "__main__":
    cfg = Config()
    web.run_app(
        create_app(),
        host=cfg.APP_HOST,
        port=cfg.APP_PORT,
    )