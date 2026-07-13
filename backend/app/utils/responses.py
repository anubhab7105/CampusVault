"""Response envelope helpers, matching the format locked in 08_API_GUIDE.md."""
from typing import Any

from flask import jsonify


def success(data: Any = None, message: str = "OK", status: int = 200):
    body = {"success": True, "message": message, "data": data if data is not None else {}}
    return jsonify(body), status


def error(code: str, message: str, status: int = 400):
    body = {"success": False, "error": {"code": code, "message": message}}
    return jsonify(body), status
