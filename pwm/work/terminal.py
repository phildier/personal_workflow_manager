from __future__ import annotations

from contextlib import contextmanager
import os
import sys
from typing import Iterator


def _configure_readline_backspace() -> None:
    """Ensure both DEL and Ctrl-H act as backspace in readline."""
    try:
        import readline
    except ImportError:
        return

    bindings = [
        '"\\C-h": backward-delete-char',
        '"\\C-?": backward-delete-char',
    ]
    for binding in bindings:
        try:
            readline.parse_and_bind(binding)
        except Exception:
            pass


def _is_delete_char(value: object) -> bool:
    """Return True when value is terminal DEL (0x7f)."""
    return value in (127, "\x7f", b"\x7f")


def _to_delete_char(example: object) -> object:
    """Return DEL in same type used by termios cc array."""
    if isinstance(example, int):
        return 127
    if isinstance(example, str):
        return "\x7f"
    return b"\x7f"


@contextmanager
def ensure_backspace_support() -> Iterator[None]:
    """Temporarily set terminal erase key to DEL while prompting."""
    _configure_readline_backspace()

    try:
        import termios
    except ImportError:
        yield
        return

    fd = None
    should_close_fd = False

    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        should_close_fd = True
    except OSError:
        if not sys.stdin.isatty():
            yield
            return
        fd = sys.stdin.fileno()

    try:
        attrs = termios.tcgetattr(fd)
    except termios.error:
        if should_close_fd:
            try:
                os.close(fd)
            except OSError:
                pass
        yield
        return

    cc = attrs[6]
    erase_index = termios.VERASE
    original_erase = cc[erase_index]

    if _is_delete_char(original_erase):
        yield
        return

    updated_attrs = attrs.copy()
    updated_cc = list(cc)
    updated_cc[erase_index] = _to_delete_char(original_erase)
    updated_attrs[6] = updated_cc

    try:
        termios.tcsetattr(fd, termios.TCSANOW, updated_attrs)
    except termios.error:
        if should_close_fd:
            try:
                os.close(fd)
            except OSError:
                pass
        yield
        return

    restored = False

    def restore_terminal() -> None:
        nonlocal restored
        if restored:
            return
        restored = True

        restore_attrs = attrs.copy()
        restore_cc = list(cc)
        restore_cc[erase_index] = original_erase
        restore_attrs[6] = restore_cc
        try:
            termios.tcsetattr(fd, termios.TCSANOW, restore_attrs)
        except termios.error:
            pass

    previous_handlers: dict[object, object] = {}

    try:
        import signal

        signals = [signal.SIGINT, signal.SIGTERM]
        sigquit = getattr(signal, "SIGQUIT", None)
        if sigquit is not None:
            signals.append(sigquit)

        def handle_signal(signum, frame):
            restore_terminal()
            previous = previous_handlers.get(signum, signal.SIG_DFL)

            if callable(previous):
                previous(signum, frame)
                return
            if previous == signal.SIG_IGN:
                return

            try:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)
            except Exception:
                raise SystemExit(128 + int(signum))

        for sig in signals:
            try:
                previous_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, handle_signal)
            except (ValueError, OSError, RuntimeError):
                pass
    except ImportError:
        signal = None

    def restore_signal_handlers() -> None:
        if not previous_handlers:
            return

        signal_module = sys.modules.get("signal")
        if signal_module is None:
            return

        for sig, handler in previous_handlers.items():
            try:
                signal_module.signal(sig, handler)
            except (ValueError, OSError, RuntimeError):
                pass

    try:
        yield
    finally:
        restore_signal_handlers()
        restore_terminal()
        if should_close_fd:
            try:
                os.close(fd)
            except OSError:
                pass
