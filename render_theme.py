import asyncio
from isd_tui.isd import InteractiveSystemd


async def render():
    app = InteractiveSystemd()
    async with app.run_test() as pilot:
        pilot.app.save_screenshot("theme.svg", "./")


asyncio.run(render())
