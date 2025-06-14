import os
import difflib
from pathlib import Path
import curses

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
            stdscr.addstr(6 + show_count, 0, "  [a] Add to 'missing songs' file")
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
                return "MANUAL_ENTRY"
            elif key == ord('a'):
                curses.endwin()
                add_to_missing_songs_file(broken_path)
                return None
            elif key == ord('v') and show_count < max_show_count:
                show_count = min(show_count + 5, max_show_count)

    if not matches_with_scores:
        print(f"\nBroken entry: {broken_path}")
        print("No automatic matches found.")
        new_path = input("Enter new path manually or leave blank to skip: ").strip()
        if not new_path:
            add_to_missing_songs_file(broken_path)
        return new_path if new_path else None
    
    selection = curses.wrapper(curses_menu)

    if selection == "MANUAL_ENTRY":
        manual = input("Enter the full replacement path: ").strip()
        return manual if manual else None
    else:
        return selection


def add_to_missing_songs_file(broken_path):
    missing_songs_file = OUTPUT_DIR / "missing_songs.txt"
    with open(missing_songs_file, "a", encoding="utf-8") as f:
        artist, song = parse_artist_and_song(broken_path)
        f.write(f"{artist} - {song}\n")
    print(f"🎵 Added to 'missing songs' file: {broken_path}")


def parse_artist_and_song(broken_path):
    # Attempt to parse artist and song from the filename
    filename = os.path.basename(broken_path)
    parts = filename.rsplit("-", 1)
    if len(parts) == 2:
        artist = parts[0].strip()
        song = parts[1].rsplit(".", 1)[0].strip()
    else:
        artist = "Unknown Artist"
        song = filename.rsplit(".", 1)[0].strip()
    return artist, song

def fix_playlist(m3u_path, music_files):
    playlist_base = m3u_path.parent.resolve()
    lines = []
    broken_entries = []

    # Load playlist
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

    output_path = OUTPUT_DIR / m3u_path.name

    # Prompt and save after each fix
    for i, (idx, orig_line, full_path) in enumerate(broken_entries, start=1):
        print(f"Processing broken entry {i} of {len(broken_entries)}")
        match = find_best_match_with_prompt(full_path, music_files)
        if match:
            try:
                rel_path = os.path.relpath(match, start=OUTPUT_DIR.resolve())
                lines[idx] = rel_path
            except ValueError:
                lines[idx] = match  # fallback to absolute

            # Save playlist after this fix
            with open(output_path, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            print(f"💾 Saved progress to: {output_path}")

    return lines




def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    music_files = get_all_music_files(MUSIC_DIR)

    playlist_files = list(PLAYLIST_DIR.glob("*.m3u8"))
    if not playlist_files:
        print("No .m3u8 playlists found in the specified directory.")
        return
    total_playlists = len(playlist_files)
    for idx, playlist_file in enumerate(playlist_files, start=1):
        print(f"\n🎧 Processing playlist {idx} of {total_playlists}: {playlist_file.name}")
        # Check for broken entries before prompting
        with open(playlist_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        broken = []
        playlist_base = playlist_file.parent.resolve()
        for line in lines:
            original_path = Path(line)
            full_path = (playlist_base / original_path).resolve() if not original_path.is_absolute() else original_path
            if not full_path.exists():
                broken.append(line)
        if broken:
            user_input = input(f"Press Enter to process, or type 's' to skip this playlist: ").strip().lower()
            if user_input == 's':
                print(f"⏭️ Skipped playlist: {playlist_file.name}")
                continue
        fixed = fix_playlist(playlist_file, music_files)
        output_path = OUTPUT_DIR / playlist_file.name
        with open(output_path, "w", encoding="utf-8") as f:
            for line in fixed:
                f.write(line + "\n")
        print(f"✅ Saved fixed playlist: {output_path}")

if __name__ == "__main__":
    main()
