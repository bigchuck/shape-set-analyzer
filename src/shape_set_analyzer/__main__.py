"""Command-line entry point for Shape Set Analyzer."""

from shape_set_analyzer import __version__


def main() -> None:
    """Run the initial Shape Set Analyzer command loop."""
    print(f"Shape Set Analyzer {__version__}")
    print("Type 'help' for assistance or 'quit' to exit.")
    print()

    while True:
        try:
            command = input("shape-analyzer> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        if not command:
            continue

        command_lower = command.lower()

        if command_lower in {"quit", "exit"}:
            break

        if command_lower == "help":
            print()
            print("Available commands:")
            print("  help    Show this help")
            print("  quit    Exit the program")
            print()
            continue

        print(f"Unknown command: {command}")
        print("Type 'help' to see available commands.")


if __name__ == "__main__":
    main()