import sys
import json
from pathlib import Path

def print_timeline(session_id: str):
    session_dir = Path(__file__).parent / "state" / "sessions" / session_id
    nodes_dir = session_dir / "nodes"
    
    if not nodes_dir.exists():
        print(f"Session directory not found: {session_dir}")
        return

    node_files = sorted(nodes_dir.glob("n_*.json"))
    states = []
    
    for f in node_files:
        with open(f) as fh:
            states.append(json.load(fh))

    if not states:
        print("No nodes found in session.")
        return

    # Find base start time
    session_start = min(s["started_at"] for s in states)
    session_end = max(s["completed_at"] for s in states)
    
    # Sort nodes by start time
    states.sort(key=lambda x: x["started_at"])

    print(f"\nTimeline for Session: {session_id}")
    print(f"{'Node':<6} {'Skill':<18} {'Start (rel)':<12} {'Elapsed':<10} {'Finish (rel)':<12}")
    print("─" * 62)

    sum_of_elapsed = 0.0
    for s in states:
        node_id = s["node_id"]
        skill = s["skill"]
        start_rel = s["started_at"] - session_start
        elapsed = s["result"]["elapsed_s"] if s.get("result") else 0.0
        finish_rel = s["completed_at"] - session_start
        sum_of_elapsed += elapsed

        print(f"{node_id:<6} {skill:<18} {start_rel:>8.2f} s    {elapsed:>6.2f} s    {finish_rel:>8.2f} s")

    wall_clock = session_end - session_start
    speedup = sum_of_elapsed / wall_clock if wall_clock > 0 else 1.0

    print("─" * 62)
    print(f"Wall-clock end-to-end:    {wall_clock:>8.2f} s")
    print(f"Sum-of-elapsed (serial):   {sum_of_elapsed:>8.2f} s")
    print(f"Parallel speedup ratio:    {speedup:>8.2f}x")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python timeline.py <session_id>")
    else:
        print_timeline(sys.argv[1])
