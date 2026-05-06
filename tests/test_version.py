from typer.testing import CliRunner

import lem
from lem.cli import app

runner = CliRunner()


def test_version_attribute_exists():
    assert hasattr(lem, "__version__")
    assert isinstance(lem.__version__, str)
    assert lem.__version__ != ""


def test_version_flag_prints_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert lem.__version__ in result.output
