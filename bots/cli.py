"""Command-line interface for bot."""

import sys
from typing import Optional

import click
import pydantic_ai
from rich.console import Console

from bots.config import DEFAULT_BOT_EMOJI
from bots.core import create_bot, delete_bot, list_bots, register_local_bot, rename_bot, run_session

console = Console()


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Modular CLI AI Assistants.

    BOTS is a command-line tool that launches project-specific or global AI assistants
    using configurable models and behaviors. Each assistant is self-contained,
    configurable, and can interact with the command line in safe, controlled ways.
    """
    # Initialize context
    ctx.obj = {}


@main.command(name="run", help="Start a bot session")
@click.argument("name")
@click.option("--one-shot", is_flag=True, help="Run in one-shot mode")
@click.option("--debug", is_flag=True, help="Show debug information")
@click.option("--continue", "continue_session", is_flag=True, help="Continue from previous session")
def run_bot(name: str, one_shot: bool, debug: bool, continue_session: bool) -> None:
    """Start a session with a bot.

    Starts a session with the specified bot. If --one-shot is specified, reads
    from stdin for the prompt. If --continue is specified, loads the previous
    session history.
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
            run_session(
                name, one_shot=True, prompt=prompt, debug=debug, continue_session=continue_session
            )
        else:
            console.print("[red]Error: No input provided for one-shot mode[/red]")
            sys.exit(1)
    else:
        # Interactive mode
        run_session(name, debug=debug, continue_session=continue_session)


@main.command()
@click.argument("bot_name")
@click.option("--local", is_flag=True, help="Create a local bot in ./.bots/ directory")
@click.option("--description", "-d", help="Description of the bot's purpose or capabilities")
def init(bot_name: str, local: bool, description: Optional[str] = None) -> None:
    """Create a new bot.

    Creates a new bot with the given name. By default, bots are created globally
    in ~/.config/bots/. Use --local to create a project-specific bot in ./.bots/.
    You can provide a description with --description to help identify the bot's purpose.
    """
    try:
        path = create_bot(bot_name, local=local, description=description)
        console.print(f"[green]Created new bot: {bot_name} at {path}[/green]")
        if description:
            console.print(f"[green]Description: {description}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating bot: {e}[/red]")
        sys.exit(1)


@main.command()
def list() -> None:
    """List all available bots.

    Shows all local bots (in the current directory's .bots folder),
    global bots (in ~/.config/bots/), and registered bots from other
    directories, including their descriptions if available.
    """
    try:
        bots = list_bots()
        if not bots["global"] and not bots["local"] and not bots["registered"]:
            console.print("No bots found. Create one with 'bots init <n>'")
            return

        console.print("\n[bold]Available Bots:[/bold]")

        if bots["local"]:
            console.print("\n[blue]Local Bots:[/blue]")
            for bot in bots["local"]:
                if isinstance(bot, str):
                    console.print(f"  - {bot}")
                else:
                    # Use emoji from bot info if available, otherwise default
                    emoji = bot.get("emoji", DEFAULT_BOT_EMOJI)

                    if "description" in bot:
                        console.print(
                            f"  - {emoji} {bot['name']} - [italic]{bot['description']}[/italic]"
                        )
                    else:
                        console.print(f"  - {emoji} {bot['name']}")

        if bots["global"]:
            console.print("\n[magenta]Global Bots:[/magenta]")
            for bot in bots["global"]:
                if isinstance(bot, str):
                    console.print(f"  - {bot}")
                else:
                    # Use emoji from bot info if available, otherwise default
                    emoji = bot.get("emoji", DEFAULT_BOT_EMOJI)

                    if "description" in bot:
                        console.print(
                            f"  - {emoji} {bot['name']} - [italic]{bot['description']}[/italic]"
                        )
                    else:
                        console.print(f"  - {emoji} {bot['name']}")
        
        if bots["registered"]:
            console.print("\n[green]Registered Bots:[/green]")
            for bot in bots["registered"]:
                if isinstance(bot, str):
                    console.print(f"  - {bot}")
                else:
                    # Use emoji from bot info if available, otherwise default
                    emoji = bot.get("emoji", DEFAULT_BOT_EMOJI)
                    
                    if "description" in bot:
                        console.print(
                            f"  - {emoji} {bot['name']} - [italic]{bot['description']}[/italic]"
                            f" [dim]({bot['path']})[/dim]"
                        )
                    else:
                        console.print(
                            f"  - {emoji} {bot['name']} [dim]({bot['path']})[/dim]"
                        )

    except Exception as e:
        console.print(f"[red]Error listing bots: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("old_name")
@click.argument("new_name")
def mv(old_name: str, new_name: str) -> None:
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


@main.command()
@click.argument("bot_name")
def register(bot_name: str) -> None:
    """Register a local bot for discovery from any directory.
    
    Adds a local bot to the central registry so it can be discovered
    and used from any directory on the system.
    """
    try:
        path = register_local_bot(bot_name)
        console.print(f"[green]Registered local bot '{bot_name}' at {path}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error registering bot: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("bot_name")
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation")
def rm(bot_name: str, force: bool) -> None:
    """Delete a bot.

    Completely removes the bot and all of its data, including configuration,
    system prompt, and session history. This operation cannot be undone.
    """
    try:
        if not force:
            click.confirm(
                f"This will permanently delete the bot '{bot_name}' and all its data. Continue?",
                abort=True,
            )

        path = delete_bot(bot_name)
        console.print(f"[green]Deleted bot: {bot_name} from {path}[/green]")
    except click.Abort:
        console.print("[yellow]Operation cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error deleting bot: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
