import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Ravenstack Connector - Helps manage and strengthen your Obsidian vault")
    parser.add_argument("command", help="Command to run (status, pull, check, etc.)")
    args = parser.parse_args()

    if args.command == "status":
        print("Checking vault status...")
        # We'll add real code here next
    elif args.command == "pull":
        print("Pulling latest changes from GitHub...")
        # We'll add real code here next
    else:
        print(f"Unknown command: {args.command}")
        print("Available commands: status, pull")

if __name__ == "__main__":
    main()