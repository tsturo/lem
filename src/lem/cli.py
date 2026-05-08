import typer

import lem
from lem.commands.cancel import cancel
from lem.commands.list import list_runs
from lem.commands.logs import logs
from lem.commands.refine import refine
from lem.commands.render import render
from lem.commands.rerun import rerun
from lem.commands.show import show
from lem.commands.watch import watch

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


app.command()(refine)
app.command()(watch)
app.command(name="list")(list_runs)
app.command()(show)
app.command()(logs)
app.command()(rerun)
app.command()(cancel)
app.command()(render)
