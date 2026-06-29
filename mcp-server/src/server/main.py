import logging
import asyncio
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp import FastMCP

from server.tools import (
    mcp,
    search_movies_by_description,
    get_movie_by_title,
    get_similar_movies,
    list_genres,
    get_dataset_stats,
)
from server.db import get_pool, close_pool
from config import MCP_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

TOOLS = {
    "search_movies_by_description": search_movies_by_description,
    "get_movie_by_title": get_movie_by_title,
    "get_similar_movies": get_similar_movies,
    "list_genres": list_genres,
    "get_dataset_stats": get_dataset_stats,
}


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/mcp/tool", methods=["POST"])
async def call_tool(request: Request) -> JSONResponse:
    body = await request.json()
    tool_name = body.get("tool")
    arguments = body.get("arguments", {})

    if tool_name not in TOOLS:
        return JSONResponse({"error": f"Unknown tool: {tool_name}"}, status_code=404)

    result = await TOOLS[tool_name](**arguments)

    if hasattr(result, "model_dump"):
        return JSONResponse(result.model_dump())
    elif isinstance(result, list):
        return JSONResponse([
            r.model_dump() if hasattr(r, "model_dump") else r for r in result
        ])
    else:
        return JSONResponse(result)


async def init_db() -> None:
    await get_pool()
    logger.info("Database pool ready")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init_db())
    mcp.run(transport="sse", host="0.0.0.0", port=MCP_PORT)
