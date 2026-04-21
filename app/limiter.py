from fastapi import Request
from slowapi import Limiter

from app.utils import get_client_ip


def _get_client_ip(request: Request) -> str:
    return get_client_ip(request)


limiter = Limiter(key_func=_get_client_ip)
