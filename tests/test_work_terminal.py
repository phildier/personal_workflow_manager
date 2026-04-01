import sys
from types import SimpleNamespace

from pwm.work.terminal import ensure_backspace_support


def test_ensure_backspace_support_sets_and_restores_erase(monkeypatch):
    calls = []
    erase_index = 2
    original_attrs = [0, 0, 0, 0, 0, 0, [b"\x00", b"\x00", b"\x08"]]

    class FakeStdin:
        def isatty(self):
            return True

        def fileno(self):
            return 7

    def fake_tcgetattr(fd):
        assert fd == 7
        return [
            original_attrs[0],
            original_attrs[1],
            original_attrs[2],
            original_attrs[3],
            original_attrs[4],
            original_attrs[5],
            list(original_attrs[6]),
        ]

    def fake_tcsetattr(fd, when, attrs):
        calls.append((fd, when, attrs[6][erase_index]))

    fake_termios = SimpleNamespace(
        VERASE=erase_index,
        TCSANOW=0,
        error=OSError,
        tcgetattr=fake_tcgetattr,
        tcsetattr=fake_tcsetattr,
    )

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    monkeypatch.setitem(sys.modules, "termios", fake_termios)

    with ensure_backspace_support():
        pass

    assert calls == [
        (7, 0, b"\x7f"),
        (7, 0, b"\x08"),
    ]


def test_ensure_backspace_support_noop_when_not_tty(monkeypatch):
    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", FakeStdin())

    with ensure_backspace_support():
        pass


def test_ensure_backspace_support_restores_on_exception(monkeypatch):
    calls = []
    erase_index = 1

    class FakeStdin:
        def isatty(self):
            return True

        def fileno(self):
            return 9

    def fake_tcgetattr(fd):
        assert fd == 9
        return [0, 0, 0, 0, 0, 0, [b"\x00", b"\x08"]]

    def fake_tcsetattr(fd, when, attrs):
        calls.append((fd, when, attrs[6][erase_index]))

    fake_termios = SimpleNamespace(
        VERASE=erase_index,
        TCSANOW=0,
        error=OSError,
        tcgetattr=fake_tcgetattr,
        tcsetattr=fake_tcsetattr,
    )

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    monkeypatch.setitem(sys.modules, "termios", fake_termios)

    try:
        with ensure_backspace_support():
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert calls == [
        (9, 0, b"\x7f"),
        (9, 0, b"\x08"),
    ]


def test_ensure_backspace_support_restores_on_keyboard_interrupt(monkeypatch):
    calls = []
    erase_index = 0

    class FakeStdin:
        def isatty(self):
            return True

        def fileno(self):
            return 10

    def fake_tcgetattr(fd):
        assert fd == 10
        return [0, 0, 0, 0, 0, 0, [b"\x08"]]

    def fake_tcsetattr(fd, when, attrs):
        calls.append((fd, when, attrs[6][erase_index]))

    fake_termios = SimpleNamespace(
        VERASE=erase_index,
        TCSANOW=0,
        error=OSError,
        tcgetattr=fake_tcgetattr,
        tcsetattr=fake_tcsetattr,
    )

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    monkeypatch.setitem(sys.modules, "termios", fake_termios)

    try:
        with ensure_backspace_support():
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass

    assert calls == [
        (10, 0, b"\x7f"),
        (10, 0, b"\x08"),
    ]


def test_ensure_backspace_support_restores_on_signal(monkeypatch):
    calls = []
    kill_calls = []
    handlers = {}
    erase_index = 0
    default_handler = object()
    ignore_handler = object()

    class FakeStdin:
        def isatty(self):
            return True

        def fileno(self):
            return 11

    def fake_tcgetattr(fd):
        assert fd == 11
        return [0, 0, 0, 0, 0, 0, [b"\x08"]]

    def fake_tcsetattr(fd, when, attrs):
        calls.append((fd, when, attrs[6][erase_index]))

    def fake_getsignal(_sig):
        return default_handler

    def fake_signal(sig, handler):
        handlers[sig] = handler

    fake_termios = SimpleNamespace(
        VERASE=erase_index,
        TCSANOW=0,
        error=OSError,
        tcgetattr=fake_tcgetattr,
        tcsetattr=fake_tcsetattr,
    )
    fake_signal_module = SimpleNamespace(
        SIGINT=2,
        SIGTERM=15,
        SIGQUIT=3,
        SIG_DFL=default_handler,
        SIG_IGN=ignore_handler,
        getsignal=fake_getsignal,
        signal=fake_signal,
    )

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    monkeypatch.setitem(sys.modules, "termios", fake_termios)
    monkeypatch.setitem(sys.modules, "signal", fake_signal_module)
    monkeypatch.setattr(
        "pwm.work.terminal.os.kill", lambda pid, sig: kill_calls.append((pid, sig))
    )
    monkeypatch.setattr("pwm.work.terminal.os.getpid", lambda: 1234)

    with ensure_backspace_support():
        handlers[fake_signal_module.SIGINT](fake_signal_module.SIGINT, None)

    assert calls == [
        (11, 0, b"\x7f"),
        (11, 0, b"\x08"),
    ]
    assert kill_calls == [(1234, 2)]
