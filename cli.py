#!/usr/bin/env python3
"""Interactive CLI client for the Recipe RAG Knowledge Graph."""

import asyncio
import json
import os
import sys
from dataclasses import dataclass

import aiohttp
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

load_dotenv()


@dataclass
class CLIConfig:
    """Configuration for the CLI client."""

    api_host: str = os.getenv("CLI_HOST", "localhost")  # CLI connects to localhost
    api_port: int = int(os.getenv("APP_PORT", "8058"))
    history_file: str = ".recipe_cli_history"

    @property
    def base_url(self) -> str:
        """Get the base API URL."""
        return f"http://{self.api_host}:{self.api_port}"


class RecipeCLI:
    """Interactive REPL client for the Recipe RAG agent."""

    # Terminal colors
    COLORS = {
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m",
    }

    def __init__(self, config: CLIConfig | None = None):
        """Initialize the CLI.

        Args:
            config: Optional configuration.
        """
        self.config = config or CLIConfig()
        self.session_id: str | None = None
        self.running = True

        # Prompt toolkit setup
        self.prompt_style = Style.from_dict(
            {
                "prompt": "#00aa00 bold",
            }
        )
        self.prompt_session = PromptSession(
            history=FileHistory(self.config.history_file),
        )

    def _color(self, text: str, color: str) -> str:
        """Apply color to text.

        Args:
            text: Text to color.
            color: Color name.

        Returns:
            Colored text string.
        """
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _print_header(self) -> None:
        """Print the CLI header."""
        print(self._color("\n Recipe RAG Knowledge Graph CLI", "bold"))
        print(self._color("=" * 40, "cyan"))
        print("Type 'help' for commands, 'exit' to quit\n")

    def _print_help(self) -> None:
        """Print help information."""
        print(self._color("\nAvailable commands:", "bold"))
        print("  help     - Show this help message")
        print("  health   - Check API health status")
        print("  clear    - Clear conversation history")
        print("  recipes  - List all available recipes")
        print("  exit     - Exit the CLI")
        print("\nOr just type a question about recipes!\n")

    async def _check_health(self) -> None:
        """Check API health status."""
        url = f"{self.config.base_url}/health"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(self._color(f"\n  API Status: {data['status']}", "green"))
                        db_status = "connected" if data.get("database") else "disconnected"
                        graph_status = (
                            "connected" if data.get("graph_database") else "disconnected"
                        )
                        llm_status = (
                            "connected" if data.get("llm_connection") else "disconnected"
                        )
                        print(f"  Database: {db_status}")
                        print(f"  Graph DB: {graph_status}")
                        print(f"  LLM: {llm_status}")
                        print(f"  Version: {data.get('version', 'unknown')}\n")
                    else:
                        print(
                            self._color(f"\n  API returned status {response.status}\n", "red")
                        )
        except aiohttp.ClientError as e:
            print(self._color(f"\n  Cannot connect to API: {e}\n", "red"))

    async def _list_recipes(self) -> None:
        """List all available recipes."""
        url = f"{self.config.base_url}/documents"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        documents = data.get("documents", [])
                        print(self._color(f"\nAvailable recipes ({len(documents)}):", "bold"))
                        for doc in documents:
                            cuisine = doc.get("metadata", {}).get("cuisine", "Unknown")
                            title = doc.get("title", doc.get("name", "Untitled"))
                            chunks = doc.get("chunk_count", 0)
                            print(f"  - {title} ({cuisine}) [{chunks} chunks]")
                        print()
                    else:
                        print(
                            self._color(
                                f"\n  Failed to list recipes: {response.status}\n", "red"
                            )
                        )
        except aiohttp.ClientError as e:
            print(self._color(f"\n  Cannot connect to API: {e}\n", "red"))

    def _format_tools_used(self, tools_list: list[dict]) -> str:
        """Format tools used for display.

        Args:
            tools_list: List of tool info dicts.

        Returns:
            Formatted string showing tools used.
        """
        if not tools_list:
            return ""

        lines = [self._color("\n  Tools used:", "cyan")]
        for i, tool in enumerate(tools_list, 1):
            name = tool.get("tool_name", tool.get("name", "unknown"))
            args = tool.get("args", {})

            # Format key arguments
            arg_parts = []
            if "query" in args:
                query = args["query"]
                if len(query) > 50:
                    query = query[:50] + "..."
                arg_parts.append(f'query="{query}"')
            if "limit" in args:
                arg_parts.append(f"limit={args['limit']}")
            if "document_id" in args:
                arg_parts.append(f'doc="{args["document_id"]}"')
            if "entity_name" in args:
                arg_parts.append(f'entity="{args["entity_name"]}"')
            if "ingredient" in args:
                arg_parts.append(f'ingredient="{args["ingredient"]}"')
            if "cuisine" in args:
                arg_parts.append(f'cuisine="{args["cuisine"]}"')
            if "recipe_name" in args:
                arg_parts.append(f'recipe="{args["recipe_name"]}"')

            args_str = ", ".join(arg_parts) if arg_parts else ""
            lines.append(
                f"    {i}. {self._color(name, 'yellow')}"
                + (f" ({args_str})" if args_str else "")
            )

        return "\n".join(lines)

    async def stream_chat(self, message: str) -> None:
        """Send a message and stream the response.

        Args:
            message: User message.
        """
        url = f"{self.config.base_url}/chat/stream"

        payload = {"message": message}
        if self.session_id:
            payload["session_id"] = self.session_id

        tools_used = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(self._color(f"\n  Error: {error_text}\n", "red"))
                        return

                    # Process SSE stream
                    print(self._color("\nAssistant: ", "green"), end="", flush=True)

                    async for line in response.content:
                        line = line.decode("utf-8").strip()

                        if not line:
                            continue

                        if line.startswith("event:"):
                            continue

                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)

                                msg_type = data.get("type", "")

                                if msg_type == "session":
                                    self.session_id = data.get("session_id")

                                elif msg_type == "text":
                                    content = data.get("content", "")
                                    print(content, end="", flush=True)

                                elif msg_type == "tools":
                                    tools_used = data.get("tools", [])

                                elif msg_type == "end":
                                    # Show tools used at the end
                                    if tools_used:
                                        print(self._format_tools_used(tools_used))
                                    print()

                                elif msg_type == "error":
                                    error = data.get("content", "Unknown error")
                                    print(
                                        self._color(f"\n  Error: {error}\n", "red")
                                    )

                            except json.JSONDecodeError:
                                continue

        except aiohttp.ClientError as e:
            print(self._color(f"\n  Connection error: {e}\n", "red"))

    async def run_repl(self) -> None:
        """Run the interactive REPL."""
        self._print_header()

        while self.running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt_session.prompt(
                        [("class:prompt", "recipe> ")],
                        style=self.prompt_style,
                    ),
                )

                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle commands
                cmd = user_input.lower()

                if cmd in ("exit", "quit"):
                    print(self._color("\nGoodbye!\n", "cyan"))
                    self.running = False

                elif cmd == "help":
                    self._print_help()

                elif cmd == "health":
                    await self._check_health()

                elif cmd == "clear":
                    self.session_id = None
                    print(self._color("\n  Conversation cleared\n", "green"))

                elif cmd == "recipes":
                    await self._list_recipes()

                else:
                    # Send message to agent
                    await self.stream_chat(user_input)

            except KeyboardInterrupt:
                print(self._color("\n\nInterrupted. Type 'exit' to quit.\n", "yellow"))

            except EOFError:
                print(self._color("\nGoodbye!\n", "cyan"))
                self.running = False


async def main() -> None:
    """Main entry point."""
    cli = RecipeCLI()
    await cli.run_repl()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
