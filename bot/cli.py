"""Command-line interface for bot."""

import sys

import click
from rich.console import Console

from bot.async_core import run_session
from bot.core import create_bot, list_bots, rename_bot

console = Console()


@click.group()
@click.pass_context
def main(ctx):
    """Modular CLI AI Assistants.

    BOT is a command-line tool that launches project-specific or global AI assistants
    using configurable models and behaviors. Each assistant is self-contained,
    configurable, and can interact with the command line in safe, controlled ways.
    """
    # Initialize context
    ctx.obj = {}


@main.command(name='run', help='Start a bot session')
@click.argument("bot_name")
def run_bot(bot_name):
    """Start a session with a bot."""
    # Check if input is from a pipe
    if not sys.stdin.isatty():
        # One-shot mode
        prompt = sys.stdin.read().strip()
        if prompt:
            run_session(bot_name, one_shot=True, prompt=prompt)
        else:
            console.print("[red]Error: No input provided for one-shot mode[/red]")
            sys.exit(1)
    else:
        # Interactive mode
        run_session(bot_name)


@main.command()
@click.argument("bot_name")
@click.option("--local", is_flag=True, help="Create a local bot in ./.bot/ directory")
def init(bot_name, local):
    """Create a new bot.

    Creates a new bot with the given name. By default, bots are created globally
    in ~/.config/bot/. Use --local to create a project-specific bot in ./.bot/.
    """
    try:
        path = create_bot(bot_name, local=local)
        console.print(f"[green]Created new bot: {bot_name} at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating bot: {e}[/red]")
        sys.exit(1)


@main.command()
def list():
    """List all available bots.

    Shows all local bots (in the current directory's .bot folder)
    and global bots (in ~/.config/bot/).
    """
    try:
        bots = list_bots()
        if not bots["global"] and not bots["local"]:
            console.print("No bots found. Create one with 'bot init <name>'")
            return

        console.print("\n[bold]Available Bots:[/bold]")

        if bots["local"]:
            console.print("\n[blue]Local Bots:[/blue]")
            for bot in bots["local"]:
                console.print(f"  - {bot}")

        if bots["global"]:
            console.print("\n[magenta]Global Bots:[/magenta]")
            for bot in bots["global"]:
                console.print(f"  - {bot}")

    except Exception as e:
        console.print(f"[red]Error listing bots: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("old_name")
@click.argument("new_name")
def mv(old_name, new_name):
    """Rename a bot.

    Renames a bot from OLD_NAME to NEW_NAME while preserving all of its
    configuration, system prompt, and session history.
    """
    try:
        path = rename_bot(old_name, new_name)
        console.print(f"[green]Renamed bot from {old_name} to {new_name} at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Error renaming bot: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
