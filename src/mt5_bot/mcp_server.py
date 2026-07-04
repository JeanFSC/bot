from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
import importlib
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mt5-full")

_MT5: Any | None = None

_BLOCKED_BY_DEFAULT = {
    "initialize",
    "login",
    "shutdown",
    "order_send",
    "symbol_select",
    "market_book_add",
    "market_book_release",
}


class MT5UnavailableError(RuntimeError):
    """Raised when the MetaTrader5 Python package is unavailable."""


def _load_dotenv_if_available() -> None:
    """Load .env when python-dotenv is installed; keep MCP usable without it."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _get_mt5() -> Any:
    """Import MetaTrader5 lazily so tests can inject a fake module."""
    global _MT5
    if _MT5 is not None:
        return _MT5
    try:
        _MT5 = importlib.import_module("MetaTrader5")
    except ImportError as exc:
        raise MT5UnavailableError(
            "MetaTrader5 package is not installed. Install project requirements "
            "and run this MCP server on Windows with MetaTrader 5 available."
        ) from exc
    return _MT5


def _last_error(mt5: Any | None = None) -> Any:
    mt5 = _get_mt5() if mt5 is None else mt5
    try:
        last_error = getattr(mt5, "last_error", None)
        if callable(last_error):
            return _json_safe(last_error())
    except Exception as exc:  # pragma: no cover - defensive only
        return {"error": repr(exc)}
    return None


def _json_safe(value: Any) -> Any:
    """Convert MetaTrader5/Python-extension return values into JSON-safe data."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "_asdict") and callable(value._asdict):
        return _json_safe(value._asdict())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=repr)]

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return _json_safe(tolist())
        except Exception:
            pass

    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except Exception:
            pass

    attrs = getattr(value, "__dict__", None)
    if isinstance(attrs, dict) and attrs:
        return {key: _json_safe(item) for key, item in attrs.items() if not key.startswith("_")}

    return repr(value)


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("$datetime value must be an ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _decode(value: Any) -> Any:
    """Decode JSON MCP arguments into values accepted by MetaTrader5."""
    if isinstance(value, Mapping):
        keys = set(value.keys())
        if keys == {"$mt5_const"}:
            name = str(value["$mt5_const"])
            return _get_constant_value(name)
        if keys == {"$datetime"}:
            return _parse_datetime(value["$datetime"])
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(item) for item in value]
    return value


def _get_constant_value(name: str) -> Any:
    if name.startswith("_"):
        raise ValueError("Only public MetaTrader5 constants can be read")
    mt5 = _get_mt5()
    if not hasattr(mt5, name):
        raise AttributeError(f"MetaTrader5 constant not found: {name}")
    value = getattr(mt5, name)
    if callable(value):
        raise TypeError(f"MetaTrader5 attribute is callable, not a constant: {name}")
    return value


def _full_access_enabled() -> bool:
    return os.getenv("MT5_MCP_ENABLE_TRADING", "").strip().lower() in {"1", "true", "yes", "on"}


def _is_blocked_by_default(name: str) -> bool:
    return name.lower() in _BLOCKED_BY_DEFAULT


def _error_payload(error: Exception | str, mt5: Any | None = None) -> dict[str, Any]:
    if isinstance(error, Exception):
        message = f"{type(error).__name__}: {error}"
    else:
        message = error
    payload: dict[str, Any] = {"success": False, "error": message}
    try:
        payload["last_error"] = _last_error(mt5)
    except Exception:
        payload["last_error"] = None
    return payload


@mcp.tool()
def mt5_list_api() -> dict[str, Any]:
    """List public MetaTrader5 callables and uppercase constants."""
    mt5 = _get_mt5()
    callables: list[str] = []
    constants: dict[str, Any] = {}
    for name in dir(mt5):
        if name.startswith("_"):
            continue
        value = getattr(mt5, name)
        if callable(value):
            callables.append(name)
        elif name.isupper():
            constants[name] = _json_safe(value)
    return {"callables": sorted(callables), "constants": dict(sorted(constants.items()))}


@mcp.tool()
def mt5_get_constant(name: str) -> dict[str, Any]:
    """Return a public MetaTrader5 constant by name."""
    try:
        return {"success": True, "name": name, "value": _json_safe(_get_constant_value(name))}
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def mt5_last_error() -> Any:
    """Return MetaTrader5.last_error()."""
    return _last_error()


@mcp.tool()
def mt5_initialize(path: str | None = None) -> dict[str, Any]:
    """Initialize the MetaTrader5 terminal connection."""
    mt5 = _get_mt5()
    try:
        ok = mt5.initialize(path=path) if path else mt5.initialize()
        return {"success": bool(ok), "initialized": bool(ok), "last_error": _last_error(mt5)}
    except Exception as exc:
        return _error_payload(exc, mt5)


@mcp.tool()
def mt5_login(login: int | str | None = None, password: str | None = None, server: str | None = None) -> dict[str, Any]:
    """Log in to MetaTrader5 using explicit args or MT5_LOGIN/PASSWORD/SERVER."""
    _load_dotenv_if_available()
    mt5 = _get_mt5()
    login_value = login if login is not None else os.getenv("MT5_LOGIN")
    password_value = password if password is not None else os.getenv("MT5_PASSWORD")
    server_value = server if server is not None else os.getenv("MT5_SERVER")

    missing = [
        name
        for name, value in {
            "MT5_LOGIN": login_value,
            "MT5_PASSWORD": password_value,
            "MT5_SERVER": server_value,
        }.items()
        if value in (None, "")
    ]
    if missing:
        return _error_payload(f"Missing MT5 credentials: {', '.join(missing)}", mt5)

    try:
        login_id = int(str(login_value))
        ok = mt5.login(login_id, password=str(password_value), server=str(server_value))
        return {"success": bool(ok), "logged_in": bool(ok), "login": login_id, "server": str(server_value), "last_error": _last_error(mt5)}
    except Exception as exc:
        return _error_payload(exc, mt5)


@mcp.tool()
def mt5_connect_from_env() -> dict[str, Any]:
    """Initialize MT5 and log in from MT5_* environment variables when present."""
    _load_dotenv_if_available()
    mt5 = _get_mt5()
    path = os.getenv("MT5_TERMINAL_PATH") or None
    initialized = mt5_initialize(path=path)
    if not initialized.get("success"):
        return initialized

    creds = {"login": os.getenv("MT5_LOGIN"), "password": os.getenv("MT5_PASSWORD"), "server": os.getenv("MT5_SERVER")}
    present = {key: bool(value) for key, value in creds.items()}
    if not any(present.values()):
        return {"success": True, "initialized": True, "logged_in": False, "last_error": _last_error(mt5)}
    if not all(present.values()):
        missing = [f"MT5_{key.upper()}" for key, has_value in present.items() if not has_value]
        return _error_payload(f"Missing MT5 credentials: {', '.join(missing)}", mt5)

    logged_in = mt5_login(login=creds["login"], password=creds["password"], server=creds["server"])
    return {
        "success": bool(logged_in.get("success")),
        "initialized": True,
        "logged_in": bool(logged_in.get("success")),
        "login": logged_in.get("login"),
        "server": logged_in.get("server"),
        "last_error": logged_in.get("last_error"),
        **({"error": logged_in["error"]} if not logged_in.get("success") and "error" in logged_in else {}),
    }


@mcp.tool()
def mt5_shutdown() -> dict[str, Any]:
    """Shutdown the MetaTrader5 terminal connection."""
    mt5 = _get_mt5()
    try:
        ok = mt5.shutdown()
        return {"success": bool(ok), "shutdown": bool(ok), "last_error": _last_error(mt5)}
    except Exception as exc:
        return _error_payload(exc, mt5)


@mcp.tool()
def mt5_call(name: str, args: list[Any] | None = None, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call any public MetaTrader5 function by name.

    Trading/state-changing functions are blocked by default. Set
    MT5_MCP_ENABLE_TRADING=1 on the MCP server process to allow the complete
    public MetaTrader5 API surface, including order_send.
    """
    mt5 = _get_mt5()
    try:
        if name.startswith("_"):
            raise ValueError("Only public MetaTrader5 names can be called")
        if not hasattr(mt5, name):
            raise AttributeError(f"MetaTrader5 function not found: {name}")
        func = getattr(mt5, name)
        if not callable(func):
            raise TypeError(f"MetaTrader5 attribute is not callable: {name}")
        if _is_blocked_by_default(name) and not _full_access_enabled():
            raise PermissionError(
                f"MetaTrader5 call '{name}' is blocked by default; set MT5_MCP_ENABLE_TRADING=1 to enable full API access"
            )
        decoded_args = _decode(args or [])
        decoded_kwargs = _decode(kwargs or {})
        result = func(*decoded_args, **decoded_kwargs)
        return {"success": True, "result": _json_safe(result), "last_error": _last_error(mt5)}
    except Exception as exc:
        return _error_payload(exc, mt5)


def main() -> None:
    """Run the MT5 MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
