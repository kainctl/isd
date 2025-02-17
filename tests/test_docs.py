from isd_tui.isd import render_model_as_yaml, get_default_settings
from rich.traceback import install

install(show_locals=True)


def test_render_model():
    render_model_as_yaml(get_default_settings())
