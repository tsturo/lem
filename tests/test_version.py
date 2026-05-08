from typer.testing import CliRunner

import lem
from lem.cli import app

runner = CliRunner()


def test_version_flag_prints_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == lem.__version__
    assert lem.__version__ != ""
