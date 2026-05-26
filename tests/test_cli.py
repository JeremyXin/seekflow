from typer.testing import CliRunner

from seekflow.cli import app


runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "seekflow 0.1.0" in result.stdout


def test_help_renders_root_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
