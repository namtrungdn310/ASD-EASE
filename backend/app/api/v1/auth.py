from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.core.security import COOKIE_NAME, issue_cookie, operator_auth, secret_matches
from app.core.wire import read_json

router = APIRouter(tags=["operator auth"])


@router.post("/auth/login")
async def login(request: Request, response: Response):
    settings = request.app.state.settings
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        raise HTTPException(403, "ORIGIN_NOT_ALLOWED")
    data = await read_json(request)
    token = data.get("token")
    if set(data) != {"token"} or not isinstance(token, str) or not secret_matches(token, settings.operator_token.get_secret_value()):
        raise HTTPException(401, "OPERATOR_AUTH_INVALID")
    response.set_cookie(COOKIE_NAME, issue_cookie(settings), max_age=3600, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/api/v1")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True, "expires_in_seconds": 3600}


@router.post("/auth/logout", dependencies=[Depends(operator_auth)])
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/api/v1")
    return {"authenticated": False}
