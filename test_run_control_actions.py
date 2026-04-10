import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from run_control_actions import dispatch_run, start_blowdown_thread


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg, *args):
        self.messages.append(("info", msg % args if args else msg))

    def error(self, msg, *args):
        self.messages.append(("error", msg % args if args else msg))


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self._target = target
        self.daemon = daemon

    def start(self):
        self._target()


class DummyAbortFlag:
    def __init__(self):
        self.cleared = False

    def clear(self):
        self.cleared = True


class DummyButton(dict):
    pass


class DummyApp:
    def __init__(self):
        self.btn_run = DummyButton()
        self.btn_abort = DummyButton()
        self.abort_flag = DummyAbortFlag()
        self.user_inputs = None


def test_dispatch_run_routes_to_blowdown():
    calls = []
    dispatch_run(
        "Zamana Bagli Basinç Dusurme (Blowdown)",
        blowdown_fn=lambda: calls.append("blowdown"),
        psv_fn=lambda: calls.append("psv"),
    )
    assert calls == ["blowdown"]


def test_dispatch_run_routes_to_psv():
    calls = []
    dispatch_run(
        "Gerekli Debiye Gore Emniyet Vanasi Capi (PSV Sizing)",
        blowdown_fn=lambda: calls.append("blowdown"),
        psv_fn=lambda: calls.append("psv"),
    )
    assert calls == ["psv"]


def test_start_blowdown_thread_success():
    app = DummyApp()
    logger = DummyLogger()
    errors = []
    ran = []

    worker = start_blowdown_thread(
        app,
        collect_inputs_fn=lambda: {"valve_type": "API 526", "p0_pa": 12e5},
        run_logic_target=lambda: ran.append("run"),
        logger=logger,
        showerror_fn=lambda title, msg: errors.append((title, msg)),
        thread_factory=ImmediateThread,
    )

    assert worker is not None
    assert app.btn_run["state"] == "disabled"
    assert app.btn_abort["state"] == "normal"
    assert app.abort_flag.cleared is True
    assert ran == ["run"]
    assert not errors


def test_start_blowdown_thread_failure():
    app = DummyApp()
    app.btn_run["state"] = "disabled"
    app.btn_abort["state"] = "normal"
    logger = DummyLogger()
    errors = []

    worker = start_blowdown_thread(
        app,
        collect_inputs_fn=lambda: (_ for _ in ()).throw(ValueError("bad input")),
        run_logic_target=lambda: None,
        logger=logger,
        showerror_fn=lambda title, msg: errors.append((title, msg)),
        thread_factory=ImmediateThread,
    )

    assert worker is None
    assert errors and errors[0][1] == "bad input"
    assert app.btn_run["state"] == "normal"
    assert app.btn_abort["state"] == "disabled"


if __name__ == "__main__":
    test_dispatch_run_routes_to_blowdown()
    test_dispatch_run_routes_to_psv()
    test_start_blowdown_thread_success()
    test_start_blowdown_thread_failure()
    print("TEST COMPLETED")
