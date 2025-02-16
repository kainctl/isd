import pytest
from pathlib import Path
from isd_tui.isd import parse_list_units_lines, parse_list_unit_files_lines


@pytest.mark.parametrize(
    "p",
    [
        "./test-systemd-229/list-units.txt",
        "./test-systemd-237/list-units.txt",
        "./test-systemd-245/list-units.txt",
        "./test-systemd-249/list-units.txt",
    ],
)
def test_parse_list_units(p: Path):
    file = Path(__file__).parent / p
    assert file.exists()
    data = file.read_text()
    # If no exception is raised it means that the parsing was successful
    parsed_units = parse_list_units_lines(data)
    assert len(parsed_units) == len(data.splitlines())


@pytest.mark.parametrize(
    "p",
    [
        "./test-systemd-229/list-unit-files.txt",
        "./test-systemd-237/list-unit-files.txt",
        "./test-systemd-245/list-unit-files.txt",
        "./test-systemd-249/list-unit-files.txt",
    ],
)
def test_parse_list_unit_files(p: Path):
    file = Path(__file__).parent / p
    assert file.exists()
    data = file.read_text()
    # If no exception is raised it means that the parsing was successful
    parsed_unit_files = parse_list_unit_files_lines(data)
    assert len(parsed_unit_files) == len(data.splitlines())
