"""
bot_controller.py
─────────────────
Thread-based runtime controller for individual bot instances.

Wraps run_trade() so that bots can be started and stopped
programmatically (e.g. from telegram_commander or a future dashboard)
without spawning a new process.

Usage:
    ctrl = BotController("config/pro.yaml")
    ctrl.start()
    ...
    ctrl.stop()   # graceful: sets stop-event, trade loop exits on next tick
    ctrl.join()   # wait for thread to finish
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

LOGGER = logging.getLogger("mt5_bot.controller")


class BotController:
    """Manages a single bot instance running in a background thread."""

    def __init__(
        self,
        config_path: str,
        on_stop: Callable[[str, int], None] | None = None,
    ) -> None:
        self.config_path = config_path
        self.on_stop = on_stop          # optional callback(symbol, exit_code)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._exit_code: int | None = None

    # ── public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the bot in a background daemon thread."""
        if self.is_running():
            LOGGER.warning("BotController.start() called but bot is already running")
            return
        self._stop_event.clear()
        self._exit_code = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"bot-{Path(self.config_path).stem}",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("BotController started: config=%s thread=%s", self.config_path, self._thread.name)

    def stop(self) -> None:
        """Signal the bot to stop gracefully on the next poll cycle."""
        self._stop_event.set()
        LOGGER.info("BotController stop requested: config=%s", self.config_path)

    def join(self, timeout: float | None = None) -> None:
        """Block until the bot thread exits (or timeout expires)."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def exit_code(self) -> int | None:
        """Last exit code from run_trade(); None if still running."""
        return self._exit_code

    # ── internal ────────────────────────────────────────────────────────────

    def _run(self) -> None:
        symbol = Path(self.config_path).stem
        try:
            self._exit_code = _run_trade_with_stop(
                self.config_path,
                self._stop_event,
            )
        except Exception:
            LOGGER.exception("BotController: unhandled exception for config=%s", self.config_path)
            self._exit_code = 1
        finally:
            LOGGER.info(
                "BotController exited: config=%s exit_code=%s",
                self.config_path, self._exit_code,
            )
            if self.on_stop:
                try:
                    self.on_stop(symbol, self._exit_code or 1)
                except Exception:
                    pass


def _run_trade_with_stop(config_path: str, stop_event: threading.Event) -> int:
    """
    Runs run_trade() and respects the stop_event between restart attempts.
    exit_code=0 means clean shutdown (do not restart).
    exit_code!=0 means crash (restart after 10s unless stop was requested).
    """
    from mt5_bot.cli import run_trade

    while not stop_event.is_set():
        exit_code = run_trade(config_path, trade_enabled_override=True)
        if exit_code == 0:
            return 0
        LOGGER.warning("Bot exited with code %s — restarting in 10s", exit_code)
        for _ in range(10):
            if stop_event.is_set():
                return 1
            time.sleep(1)

    return 0
