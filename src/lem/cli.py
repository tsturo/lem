import typer

import lem

app = typer.Typer()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(lem.__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass
