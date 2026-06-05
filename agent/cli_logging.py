import asyncio
import contextlib
import sys
from pathlib import Path
from typing import Type, Generator

class TeeStream:
    """Stream wrapper that writes to both an original stream (e.g. stdout) and a log file."""
    def __init__(self, original_stream, file_obj):
        self.original_stream = original_stream
        self.file_obj = file_obj

    def write(self, data):
        self.original_stream.write(data)
        self.original_stream.flush()
        self.file_obj.write(data)
        self.file_obj.flush()

    def flush(self):
        self.original_stream.flush()
        self.file_obj.flush()

    def isatty(self):
        return self.original_stream.isatty()

    def fileno(self):
        return self.original_stream.fileno()


@contextlib.contextmanager
def tee_output(log_path: Path, mode: str = "w") -> Generator[None, None, None]:
    """Context manager to tee stdout and stderr to a file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, mode, encoding="utf-8", buffering=1) as f:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TeeStream(original_stdout, f)
        sys.stderr = TeeStream(original_stderr, f)
        try:
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


async def interactive_loop(executor_cls: Type) -> None:
    """Interactive loop for entering and running queries."""
    print("Welcome to the Interactive Agent Loop!")
    print("Type your queries below. Type 'exit', 'quit', or press Ctrl+D to exit.")
    executor = executor_cls()
    while True:
        try:
            query = input("\nQuery > ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive loop.")
            break
        query = query.strip()
        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Exiting interactive loop.")
            break
        try:
            await executor.run(query)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


def run_cli(executor_cls: Type) -> None:
    """Main CLI entry point that routes to single-run, resume, or interactive loop."""
    args = sys.argv[1:]
    resume_sid: str | None = None
    
    interactive = False
    if args and args[0] in ("-i", "--interactive"):
        interactive = True
        args = args[1:]
        
    if args and args[0] == "--resume":
        resume_sid = args[1] if len(args) > 1 else None
        query = " ".join(args[2:])
    else:
        query = " ".join(args) or "Say hello in one short sentence."
        
    if interactive or (not query and not resume_sid):
        asyncio.run(interactive_loop(executor_cls))
    else:
        asyncio.run(executor_cls().run(query, session_id=resume_sid, resume=bool(resume_sid)))
