"""Command-line interface for bot."""

import sys

import click
import pydantic_ai
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


@main.command(name="run", help="Start a bot session")
@click.option("--name", "-n", required=True, help="Name of the bot to start a session with")
@click.option("--one-shot", is_flag=True, help="Run in one-shot mode")
@click.option("--debug", is_flag=True, help="Show debug information")
def run_bot(name, one_shot, debug):
    """Start a session with a bot.
    
    Starts an interactive session with the specified bot. If --one-shot is specified,
    reads from stdin for the prompt.
    """
    if debug:
        console.print("[bold blue]Debug Information:[/bold blue]")
        console.print(f"Python version: {sys.version}")
        console.print(f"Python executable: {sys.executable}")
        console.print(f"pydantic-ai version: {getattr(pydantic_ai, '__version__', 'unknown')}")
        
        # Check for API key
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            console.print(f"OPENAI_API_KEY: [green]Present[/green] ({len(api_key)} chars)")
        else:
            console.print("OPENAI_API_KEY: [red]Not found in environment[/red]")
        console.print("")
    
    if one_shot:
        # One-shot mode
        prompt = sys.stdin.read().strip()
        if prompt:
            run_session(name, one_shot=True, prompt=prompt, debug=debug)
        else:
            console.print("[red]Error: No input provided for one-shot mode[/red]")
            sys.exit(1)
    else:
        # Interactive mode
        run_session(name, debug=debug)


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
            console.print("No bots found. Create one with 'bot init <n>'")
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