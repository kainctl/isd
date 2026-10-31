import asyncio
import signal
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock

import pytest

import isd_tui.isd as isd


class FakeApp:
    """Minimal stand-in for `textual.app.App` for suspend tests."""

    def __init__(self) -> None:
        self.suspended = False
        self.resumed = False

    @contextmanager
    def suspend(self):
        self.suspended = True
        yield
        self.resumed = True


class FakeStdin:
    """Minimal stand-in for an interactive stdin."""

    def isatty(self) -> bool:
        return True


class FakeMainScreen:
    """Minimal stand-in for the parts of `MainScreen` used by the sudo flow."""

    def __init__(self, *, mode: str = "system", can_use_sudo: bool = True) -> None:
        self.mode = mode
        self.relevant_units = ["foo.service"]
        self.app = FakeApp()
        self._sudo_auth_lock = asyncio.Lock()
        self._can_use_sudo = lambda: can_use_sudo
        self.notifications: list[tuple] = []
        self.successes: list[str] = []

    def notify(self, message, **kwargs) -> None:
        self.notifications.append((message, kwargs))

    def _notify_systemctl_success(self, unsplit_command: str) -> None:
        self.successes.append(unsplit_command)

    def _notify_systemctl_error(
        self,
        unsplit_command: str,
        return_code: int,
        stderr: str,
        stdout: str,
    ) -> None:
        self.notifications.append(
            ("systemctl-error", unsplit_command, return_code, stderr, stdout)
        )


def fake_which(name: str):
    return "/usr/bin/sudo" if name == "sudo" else None


def test_safe_app_suspend_resumes_on_exception():
    app = FakeApp()

    with pytest.raises(RuntimeError, match="boom"):
        with isd.safe_app_suspend(app):
            raise RuntimeError("boom")

    assert app.suspended
    assert app.resumed


def test_safe_app_suspend_resumes_normally():
    app = FakeApp()

    with isd.safe_app_suspend(app):
        pass

    assert app.suspended
    assert app.resumed


def test_safe_app_suspend_restores_sigint_handler():
    app = FakeApp()
    previous_handler = signal.getsignal(signal.SIGINT)

    with isd.safe_app_suspend(app):
        assert signal.getsignal(signal.SIGINT) is not previous_handler

    assert signal.getsignal(signal.SIGINT) is previous_handler


def test_authenticate_sudo_shows_executed_command(monkeypatch):
    app = FakeApp()
    shown_commands = []
    monkeypatch.setattr(
        isd, "show_command", lambda *args: shown_commands.append(args)
    )
    subprocess_call = Mock(return_value=0)
    monkeypatch.setattr(isd.subprocess, "call", subprocess_call)
    monkeypatch.setattr(isd.sys, "stdin", FakeStdin())

    command = [
        "sudo",
        "--preserve-env",
        "systemctl",
        "start",
        "--",
        "foo.service",
    ]
    return_code = isd.authenticate_sudo(app, command)

    assert return_code == 0
    assert shown_commands == [tuple(command)]
    # The password prompt is implemented with `sudo --validate`, but that is
    # deliberately not shown to the user.
    subprocess_call.assert_called_once_with(["sudo", "--validate"])


def test_systemctl_args_builder_uses_non_interactive_sudo(monkeypatch):
    monkeypatch.setattr(isd, "is_root", lambda: False)

    args = isd.systemctl_args_builder(
        "start",
        mode="system",
        units=["foo.service"],
        sudo=True,
        ask_password=False,
        non_interactive=True,
    )

    assert args == [
        "sudo",
        "--non-interactive",
        "--preserve-env",
        "systemctl",
        "start",
        "--",
        "foo.service",
    ]


def test_systemctl_args_builder_forwards_environment(monkeypatch):
    monkeypatch.setattr(isd, "is_root", lambda: False)

    args = isd.systemctl_args_builder(
        "edit", mode="system", units=["foo.service"], sudo=True
    )

    # `systemctl edit` needs the user's `SYSTEMD_EDITOR`/`EDITOR`, so the
    # environment is forwarded intentionally. The obsolete stdin probe must
    # stay removed.
    assert args[:2] == ["sudo", "--preserve-env"]
    assert "--stdin" not in args


def test_systemctl_args_builder_only_disables_ask_password_unprivileged(
    monkeypatch,
):
    monkeypatch.setattr(isd, "is_root", lambda: False)

    unprivileged = isd.systemctl_args_builder(
        "start", mode="system", units=["foo.service"], ask_password=False
    )
    privileged = isd.systemctl_args_builder(
        "start",
        mode="system",
        units=["foo.service"],
        sudo=True,
        ask_password=False,
    )

    # Prevents polkit on the unprivileged probe.
    assert "--no-ask-password" in unprivileged
    # Redundant (and confusing in the displayed command) when running as root.
    assert "--no-ask-password" not in privileged


def test_systemctl_args_builder_skips_sudo_for_root(monkeypatch):
    monkeypatch.setattr(isd, "is_root", lambda: True)

    args = isd.systemctl_args_builder(
        "start", mode="system", units=["foo.service"], sudo=True
    )

    assert args[0] == "systemctl"


def test_systemctl_args_builder_user_mode(monkeypatch):
    monkeypatch.setattr(isd, "is_root", lambda: False)

    args = isd.systemctl_args_builder(
        "start", mode="user", units=["foo.service"], sudo=True
    )

    assert args[:3] == ["sudo", "--preserve-env", "systemctl"]
    assert args[3] == "--user"


def test_journalctl_args_builder_non_interactive_sudo(monkeypatch):
    monkeypatch.setattr(isd, "is_root", lambda: False)

    args = isd.journalctl_args_builder(
        "--lines=10",
        mode="system",
        units=["foo.service"],
        sudo=True,
        non_interactive=True,
    )

    assert args == [
        "sudo",
        "--non-interactive",
        "--preserve-env",
        "journalctl",
        "--lines=10",
        "--unit",
        "foo.service",
    ]


@pytest.mark.parametrize(
    "stderr",
    [
        "Failed to start foo.service: Interactive authentication required.",
        "Reload daemon failed: Access denied as the requested operation "
        "requires interactive authentication.",
        "Failed to enable unit: Access denied",
        "Authentication is required to start foo.service.",
        "Permission denied",
    ],
)
def test_stderr_requires_authentication(stderr):
    assert isd.stderr_requires_authentication(stderr)


@pytest.mark.parametrize(
    "stderr",
    [
        "Failed to start foo.service: Unit foo.service not found.",
        "Failed to start foo.service: Connection timed out",
        "Unknown command verb 'xyz'.",
        "",
    ],
)
def test_stderr_does_not_require_authentication(stderr):
    assert not isd.stderr_requires_authentication(stderr)


@pytest.mark.parametrize(
    "stderr",
    [
        "sudo: user is not allowed to run sudo",
        "sudo: user is not in the sudoers file. This incident will be reported.",
        "sudo: user may not run sudo",
    ],
)
def test_sudo_is_not_allowed(stderr):
    assert isd.sudo_is_not_allowed(stderr)


def test_sudo_is_not_allowed_password_required():
    assert not isd.sudo_is_not_allowed("sudo: a password is required")


async def test_run_systemctl_command_uses_cached_sudo(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    monkeypatch.setattr(
        isd,
        "systemctl_async",
        AsyncMock(
            side_effect=[
                (1, "", "Interactive authentication required."),
                (0, "", ""),
            ]
        ),
    )
    monkeypatch.setattr(
        isd, "sudo_credentials_are_cached", AsyncMock(return_value=(True, ""))
    )
    authenticate_sudo = Mock(return_value=0)
    monkeypatch.setattr(isd, "authenticate_sudo", authenticate_sudo)

    screen = FakeMainScreen()
    await isd.MainScreen._run_systemctl_command(screen, "start")

    authenticate_sudo.assert_not_called()
    assert screen.successes == ["start"]
    assert isd.systemctl_async.await_args_list[1].kwargs["sudo"] is True
    assert isd.systemctl_async.await_args_list[1].kwargs["non_interactive"] is True


async def test_run_systemctl_command_authenticates_then_runs(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    monkeypatch.setattr(
        isd,
        "systemctl_async",
        AsyncMock(
            side_effect=[
                (1, "", "Interactive authentication required."),
                (0, "", ""),
            ]
        ),
    )
    monkeypatch.setattr(
        isd,
        "sudo_credentials_are_cached",
        AsyncMock(
            side_effect=[
                (False, "sudo: a password is required"),
                (True, ""),
            ]
        ),
    )
    authenticate_sudo = Mock(return_value=0)
    monkeypatch.setattr(isd, "authenticate_sudo", authenticate_sudo)

    screen = FakeMainScreen()
    await isd.MainScreen._run_systemctl_command(screen, "start")

    authenticate_sudo.assert_called_once_with(
        screen.app,
        [
            "sudo",
            "--preserve-env",
            "systemctl",
            "start",
            "--",
            "foo.service",
        ],
    )
    assert screen.successes == ["start"]
    assert isd.SUDO_CREDENTIALS_ARE_NOT_CACHED is False
    assert isd.systemctl_async.await_args_list[1].kwargs["sudo"] is True
    assert isd.systemctl_async.await_args_list[1].kwargs["non_interactive"] is True


async def test_run_systemctl_command_auth_failure_does_not_execute(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    systemctl_async = AsyncMock(
        return_value=(1, "", "Interactive authentication required.")
    )
    monkeypatch.setattr(isd, "systemctl_async", systemctl_async)
    monkeypatch.setattr(
        isd,
        "sudo_credentials_are_cached",
        AsyncMock(return_value=(False, "sudo: a password is required")),
    )
    authenticate_sudo = Mock(return_value=1)
    monkeypatch.setattr(isd, "authenticate_sudo", authenticate_sudo)

    screen = FakeMainScreen()
    await isd.MainScreen._run_systemctl_command(screen, "start")

    # Only the unprivileged attempt ran; the actual command was not repeated.
    assert systemctl_async.await_count == 1
    assert any(
        "Authentication failed or was cancelled" in notification[0]
        for notification in screen.notifications
        if notification and isinstance(notification[0], str)
    )


async def test_run_systemctl_command_non_auth_error_is_reported(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    monkeypatch.setattr(
        isd,
        "systemctl_async",
        AsyncMock(return_value=(1, "", "Unit foo.service not found.")),
    )
    authenticate_sudo = Mock(return_value=0)
    monkeypatch.setattr(isd, "authenticate_sudo", authenticate_sudo)

    screen = FakeMainScreen()
    await isd.MainScreen._run_systemctl_command(screen, "start")

    authenticate_sudo.assert_not_called()
    assert screen.successes == []
    assert any(
        notification[0] == "systemctl-error"
        for notification in screen.notifications
    )


async def test_run_systemctl_command_no_caching_uses_blocking_calls(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    monkeypatch.setattr(
        isd,
        "systemctl_async",
        AsyncMock(return_value=(1, "", "Interactive authentication required.")),
    )
    monkeypatch.setattr(
        isd,
        "sudo_credentials_are_cached",
        AsyncMock(return_value=(False, "sudo: a password is required")),
    )
    monkeypatch.setattr(isd, "authenticate_sudo", Mock(return_value=0))
    run_blocking = Mock(return_value=0)
    monkeypatch.setattr(isd, "run_blocking_in_suspend", run_blocking)

    screen = FakeMainScreen()
    await isd.MainScreen._run_systemctl_command(screen, "start")

    assert isd.SUDO_CREDENTIALS_ARE_NOT_CACHED is True
    run_blocking.assert_called_once()
    assert screen.successes == ["start"]


async def test_run_systemctl_command_user_mode_never_uses_sudo(monkeypatch):
    monkeypatch.setattr(isd, "SUDO_CREDENTIALS_ARE_NOT_CACHED", False)
    monkeypatch.setattr(isd.shutil, "which", fake_which)
    monkeypatch.setattr(
        isd,
        "systemctl_async",
        AsyncMock(return_value=(1, "", "Interactive authentication required.")),
    )
    authenticate_sudo = Mock(return_value=0)
    monkeypatch.setattr(isd, "authenticate_sudo", authenticate_sudo)

    screen = FakeMainScreen(mode="user", can_use_sudo=False)
    await isd.MainScreen._run_systemctl_command(screen, "start")

    authenticate_sudo.assert_not_called()
    assert screen.successes == []
