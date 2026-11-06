"""全局异常处理：统一错误响应为 {detail: str} 格式，不泄露内部堆栈。"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("app.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        detail = "请求参数错误"
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = [str(x) for x in first.get("loc", []) if x not in ("body", "query", "path")]
            msg = first.get("msg", "")
            field = loc[-1] if loc else ""
            detail = f"参数「{field}」校验失败：{msg}" if field else f"参数校验失败：{msg}"
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail})

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        logger.warning("IntegrityError on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "数据冲突，可能已存在相同记录"})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "服务器内部错误，请稍后重试"})
