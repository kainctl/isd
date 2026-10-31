import pytest

from isd_tui.isd import InteractiveSystemd


@pytest.fixture(autouse=True)
def cancel_workers_before_test_shutdown(monkeypatch):
    """Cancel workers before ``run_test()`` tears down the app.

    ``App.run_test()`` calls ``_shutdown()`` directly, before the message
    loop's normal worker cleanup. Without this, a throttled worker may wake
    up while Textual is pruning screens and query widgets that are already
    gone. This patch only applies to tests.
    """
    original_shutdown = InteractiveSystemd._shutdown

    async def shutdown_with_cancelled_workers(self) -> None:
        self.workers.cancel_all()
        await original_shutdown(self)

    monkeypatch.setattr(
        InteractiveSystemd, "_shutdown", shutdown_with_cancelled_workers
    )
