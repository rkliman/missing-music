import os
import difflib
from pathlib import Path
import curses
import subprocess  # Import subprocess to run shell commands

PLAYLIST_DIR = Path("/home/randall/Music")   # Update this
MUSIC_DIR = Path("/home/randall/Music")          # Update this
OUTPUT_DIR = Path("/home/randall/Music")  # Update this

def get_all_music_files(music_dir):
    return [str(p.resolve()) for p in music_dir.rglob("*") if p.is_file()]

def find_best_match_with_prompt(broken_path, candidates):
    filename = os.path.basename(broken_path)
    matches_with_scores = [(c, difflib.SequenceMatcher(None, filename, os.path.basename(c)).ratio()) for c in candidates]
    matches_with_scores = sorted(matches_with_scores, key=lambda x: x[1], reverse=True)

    # Automatically fix if the best match has a score > 0.95
    if matches_with_scores and matches_with_scores[0][1] >= 0.9:
        print(f"✅ Automatically fixing {broken_path} with {matches_with_scores[0][0]} (Score: {matches_with_scores[0][1]:.2f})")
        return matches_with_scores[0][0]

    def curses_menu(stdscr):
        curses.curs_set(0)
        stdscr.clear()
        current_row = 0
        show_count = 5  # Number of matches to show initially
        max_show_count = len(matches_with_scores)

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, f"Broken entry: {broken_path}")
            stdscr.addstr(2, 0, "Possible matches:")
            for idx, (full_path, score) in enumerate(matches_with_scores[:show_count]):
                if idx == current_row:
                    stdscr.addstr(4 + idx, 0, f"> {full_path} (Score: {score:.2f})", curses.A_REVERSE)
                else:
                    stdscr.addstr(4 + idx, 0, f"  {full_path} (Score: {score:.2f})")
            stdscr.addstr(4 + show_count, 0, "  [s] Skip")
            stdscr.addstr(5 + show_count, 0, "  [m] Manual entry")
            stdscr.addstr(6 + show_count, 0, "  [r] Rip from streamrip")
            if show_count < max_show_count:
                stdscr.addstr(7 + show_count, 0, "  [v] View more matches")
            stdscr.refresh()

            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < min(len(matches_with_scores), show_count) - 1:
                current_row += 1
            elif key in (curses.KEY_ENTER, 10, 13):  # Enter key
                return matches_with_scores[current_row][0]
            elif key == ord('s'):
                return None
            elif key == ord('m'):
                curses.endwin()
                manual = input("Enter the full replacement path: ").strip()
                return manual if manual else None
            elif key == ord('r'):
                curses.endwin()
                # Extract artist and song from the filename
                artist, song = os.path.splitext(filename)[0].split(" - ", 1)
                print(f"🎵 Searching for '{artist} - {song}' on streamrip...")
                try:
                    # Open an interactive shell for the rip command
                    subprocess.run(["rip", "search", "tidal", f"track '{artist} - {song}'"], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"❌ Failed to rip song. Error: {e}")
                return None  # Return None after attempting to rip
            elif key == ord('v') and show_count < max_show_count:
                show_count = min(show_count + 5, max_show_count)

    if not matches_with_scores:
        print(f"\nBroken entry: {broken_path}")
        print("No automatic matches found.")
        new_path = input("Enter new path manually or leave blank to skip: ").strip()
        return new_path if new_path else None

    return curses.wrapper(curses_menu)

def fix_playlist(m3u_path, music_files):
    playlist_base = m3u_path.parent.resolve()
    lines = []
    broken_entries = []

    # First pass — collect info
    with open(m3u_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            lines.append(line)

            if not line or line.startswith("#"):
                continue

            original_path = Path(line)
            full_path = (playlist_base / original_path).resolve() if not original_path.is_absolute() else original_path

            if not full_path.exists():
                broken_entries.append((idx, line, str(full_path)))

    total_count = sum(1 for l in lines if l and not l.startswith("#"))
    print(f"🔍 Playlist: {m3u_path.name} — {len(broken_entries)} broken entries out of {total_count}\n")

    # Second pass — prompt for each broken entry
    for i, (idx, orig_line, full_path) in enumerate(broken_entries, start=1):
        print(f"Processing broken entry {i} of {len(broken_entries)}")
        match = find_best_match_with_prompt(full_path, music_files)
        if match:
            try:
                rel_path = os.path.relpath(match, start=OUTPUT_DIR.resolve())
                lines[idx] = rel_path
            except ValueError:
                lines[idx] = match  # fallback to absolute
        # else leave the original line untouched

    return lines



def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    music_files = get_all_music_files(MUSIC_DIR)

    for playlist_file in PLAYLIST_DIR.glob("*.m3u8"):
        print(f"\n🎧 Processing playlist: {playlist_file.name}")
        fixed = fix_playlist(playlist_file, music_files)
        output_path = OUTPUT_DIR / playlist_file.name
        with open(output_path, "w", encoding="utf-8") as f:
            for line in fixed:
                f.write(line + "\n")
        print(f"✅ Saved fixed playlist: {output_path}")

if __name__ == "__main__":
    main()
