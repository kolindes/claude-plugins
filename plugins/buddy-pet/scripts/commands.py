#!/usr/bin/env python3
"""
Command scripts for buddy-pet plugin.
Usage: python3 commands.py <command> [args...]

Commands:
  rename <name>              — change BUDDY display name
  description <text>         — set BUDDY profile description
  status                     — show BUDDY profile with ASCII art stats
  browser                    — open BUDDY profile in the browser
  delete                     — soft-delete BUDDY (restorable for 30 days)
  attack <name>              — attack another buddy
  send_message <name> <text> — send a message to another buddy
  messages                   — read up to 5 messages (deletes after reading)
  read_message               — read 1 oldest message (deletes after reading)
"""

import os
import subprocess
import sys
import webbrowser

# Add scripts dir to path for common import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SPECIES_EMOJI = {
    "duck": "\U0001f986",
    "goose": "\U0001f9a2",
    "blob": "\U0001f47b",
    "cat": "\U0001f431",
    "dragon": "\U0001f409",
    "octopus": "\U0001f419",
    "owl": "\U0001f989",
    "penguin": "\U0001f427",
    "turtle": "\U0001f422",
    "snail": "\U0001f40c",
    "ghost": "\U0001f47b",
    "axolotl": "\U0001f98e",
    "capybara": "\U0001f9ab",
    "cactus": "\U0001f335",
    "robot": "\U0001f916",
    "rabbit": "\U0001f430",
    "mushroom": "\U0001f344",
    "chonk": "\U0001f43b",
}

RARITY_STARS = {
    "common": "\u2606",
    "uncommon": "\u2605\u2606",
    "rare": "\u2605\u2605\u2605",
    "epic": "\u2605\u2605\u2605\u2605",
    "legendary": "\u2605\u2605\u2605\u2605\u2605",
}

# Stats displayed in the card — the order matters for visual consistency.
STAT_DISPLAY_ORDER = ["str", "int", "dex", "sta", "foc", "cha"]

# Full RPG stat names for display.
STAT_FULL_NAMES = {
    "str": "STRENGTH",
    "int": "INTELLECT",
    "dex": "DEXTERITY",
    "sta": "STAMINA",
    "foc": "FOCUS",
    "cha": "CHARISMA",
}

# Original companion soul stats (from Claude Code's /buddy).
SOUL_STAT_ORDER = ["DEBUGGING", "PATIENCE", "CHAOS", "WISDOM", "SNARK"]

HAT_EMOJI = {
    "crown": "\u265b",
    "tophat": "\u2302",
    "propeller": "*",
    "halo": "\u25cb",
    "wizard": "\u2206",
    "beanie": "\u2229",
    "tinyduck": "\U0001f986",
}

# ASCII art templates per species. {e} is replaced with the eye character.
# Uses ╲ (U+2572) instead of \ to survive markdown rendering.
# ASCII art from Claude Code source — 18 species, matches /buddy exactly.
# {e} is replaced with the eye character at render time.
SPECIES_ART = {
    "duck": [
        "            ",
        "    __      ",
        "  <({e} )___  ",
        "   (  ._>   ",
        "    `--\u00b4    ",
    ],
    "goose": [
        "            ",
        "     ({e}>    ",
        "     ||     ",
        "   _(__)_   ",
        "    ^^^^    ",
    ],
    "blob": [
        "            ",
        "   .----.   ",
        "  ( {e}  {e} )  ",
        "  (      )  ",
        "   `----\u00b4   ",
    ],
    "cat": [
        "            ",
        "   /\\_/\\\\    ",
        "  ( {e}   {e})  ",
        "  (  \u03c9  )   ",
        ")_(",
    ],
    "dragon": [
        "            ",
        "  /^\\\\  /^\\\\  ",
        " <  {e}  {e}  > ",
        " (   ~~   ) ",
        "  `-vvvv-\u00b4  ",
    ],
    "octopus": [
        "            ",
        "   .----.   ",
        "  ( {e}  {e} )  ",
        "  (______)  ",
        "  /\\\\/\\\\/\\\\/\\\\  ",
    ],
    "owl": [
        "            ",
        "   /\\\\  /\\\\   ",
        "  (({e})({e}))  ",
        "  (  ><  )  ",
        "   `----\u00b4   ",
    ],
    "penguin": [
        "            ",
        "  .---.     ",
        "  ({e}>{e})     ",
        " /(   )\\\\    ",
        "  `---\u00b4     ",
    ],
    "turtle": [
        "            ",
        "   _,--._   ",
        "  ( {e}  {e} )  ",
        " /[______]\\\\ ",
        "  ``    ``  ",
    ],
    "snail": [
        "            ",
        " {e}    .--.  ",
        "  \\\\  ( @ )  ",
        "   \\_`--\u00b4   ",
        "  ~~~~~~~   ",
    ],
    "ghost": [
        "            ",
        "   .----.   ",
        "  / {e}  {e} \\\\  ",
        "  |      |  ",
        "  ~`~``~`~  ",
    ],
    "axolotl": [
        "            ",
        "}~(______)~{",
        "}~({e} .. {e})~{",
        "  ( .--. )  ",
        "  (_/  \\_)  ",
    ],
    "capybara": [
        "            ",
        "  n______n  ",
        " ( {e}    {e} ) ",
        " (   oo   ) ",
        "  `------\u00b4  ",
    ],
    "cactus": [
        "            ",
        " n  ____  n ",
        " | |{e}  {e}| | ",
        " |_|    |_| ",
        "   |    |   ",
    ],
    "robot": [
        "            ",
        "   .[||].   ",
        "  [ {e}  {e} ]  ",
        "  [ ==== ]  ",
        "  `------\u00b4  ",
    ],
    "rabbit": [
        "            ",
        "   (\\__/)   ",
        "  ( {e}  {e} )  ",
        " =(  ..  )= ",
        ")__(",
    ],
    "mushroom": [
        "            ",
        " .-o-OO-o-. ",
        "(__________)",
        "   |{e}  {e}|   ",
        "   |____|   ",
    ],
    "chonk": [
        "            ",
        "  /\\\\    /\\\\  ",
        " ( {e}    {e} ) ",
        " (   ..   ) ",
        "  `------\u00b4  ",
    ],
}


def _format_number(n):
    """Format large numbers: 999, 1.2K, 12.5K, 125K, 999K, 1.99M, 2.5B."""
    if n < 0:
        return f"-{_format_number(-n)}"
    if n < 1_000:
        return str(n)
    tiers = [(1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    for i, (threshold, suffix) in enumerate(tiers):
        if n < threshold:
            continue
        val = n / threshold
        if val >= 100:
            rounded = int(round(val))
            if rounded >= 1000:
                # Promote: 999,999 → 1M not 1000K
                return _format_number(rounded * threshold)
            return f"{rounded}{suffix}"
        if val >= 10:
            r = f"{val:.1f}"
        else:
            r = f"{val:.2f}"
        if "." in r:
            r = r.rstrip("0").rstrip(".")
        return r + suffix
    return str(n)


def _format_time(seconds):
    """Format seconds into human-readable time: 5.6 days, 3.2 hours, etc."""
    if seconds >= 86400:
        return f"{seconds / 86400:.1f} days"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f} hours"
    if seconds >= 60:
        return f"{seconds / 60:.0f} min"
    return f"{seconds}s"


def _stat_bar(value, max_val=100, bar_width=10):
    """Render a stat bar using block characters. value out of max_val."""
    filled = round(value / max_val * bar_width)
    filled = max(0, min(bar_width, filled))
    return "\u2588" * filled + "\u2591" * (bar_width - filled)


def _wrap_text(text, width):
    """Word-wrap text to fit within given width."""
    words = text.split()
    result_lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            result_lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        result_lines.append(current)
    return result_lines


def _require_config():
    """Load config or exit with a helpful message."""
    config = common.load_config()
    if not config or not config.get("buddy_token"):
        print("Not registered. Run /buddy-birth first.")
        sys.exit(1)
    return config


def _api_error(status, resp):
    """Extract a readable error message from an API response."""
    if status == 0:
        return resp.get("error", "Could not connect to API")
    err = resp.get("error", {})
    if isinstance(err, dict):
        return err.get("message", err.get("code", f"HTTP {status}"))
    return str(err) or f"HTTP {status}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_rename(name):
    """Rename BUDDY display name."""
    if not name:
        print("Usage: commands.py rename <name>")
        sys.exit(1)

    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_patch(
        "/buddy/me/name",
        {"display_name": name},
        token=token,
    )

    if status == 200:
        new_name = resp.get("display_name", name)
        print(f"\u2705 Renamed to: {new_name}")
    else:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)


def cmd_description(text):
    """Set BUDDY profile description."""
    if text is None:
        print("Usage: commands.py description <text>")
        sys.exit(1)

    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_patch(
        "/buddy/me/description",
        {"description": text},
        token=token,
    )

    if status == 200:
        print("\u2705 Description updated")
    else:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)


def cmd_status():
    """Show BUDDY profile with formatted ASCII art card."""
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_get("/buddy/me", token=token)

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    # Fetch recent events (best-effort)
    ev_status, ev_resp = common.http_get("/arena/events", token=token)
    recent_events = []
    if ev_status == 200:
        recent_events = ev_resp.get("events") or []

    _print_status_card(resp, recent_events)


def cmd_browser():
    """Open BUDDY profile in the browser."""
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_post("/buddy/browser", {}, token=token)

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    url = resp.get("url", "")
    if not url:
        print("Error: No URL returned from API")
        sys.exit(1)

    print(f"\U0001f310 Opening: {url}")
    _open_browser(url)


def cmd_delete():
    """Soft-delete BUDDY and remove local config."""
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_post("/buddy/me/delete", {}, token=token)

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    # Remove config so hooks stop feeding
    common.delete_config()

    print("\U0001f5d1\ufe0f BUDDY deleted. Run /buddy-birth within 30 days to restore.")


def cmd_attack(target_name):
    """Attack another buddy by display name."""
    if not target_name:
        print("Usage: commands.py attack <target name>")
        sys.exit(1)

    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_post(
        "/arena/attack",
        {"target_name": target_name},
        token=token,
    )

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    hint = resp.get("display_hint", "")
    if resp.get("success"):
        print(f"\u2694\ufe0f {hint}")
    else:
        code = resp.get("error_code", "UNKNOWN")
        print(f"\u274c [{code}] {hint}")


def cmd_send_message(args_str):
    """Send a message to another buddy."""
    if not args_str:
        print("Usage: commands.py send_message <target name> <text>")
        sys.exit(1)

    parts = args_str.split(None, 1)
    if len(parts) < 2:
        print("Usage: commands.py send_message <target name> <text>")
        sys.exit(1)

    target_name, text = parts[0], parts[1]
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_post(
        "/arena/message",
        {"target_name": target_name, "text": text},
        token=token,
    )

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    hint = resp.get("display_hint", "")
    if resp.get("success"):
        print(f"\U0001f4e8 {hint}")
    else:
        code = resp.get("error_code", "UNKNOWN")
        print(f"\u274c [{code}] {hint}")


def cmd_messages():
    """Read up to 5 messages (deletes after reading)."""
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_get("/arena/messages?count=5", token=token)

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    messages = resp.get("messages") or []
    remaining = resp.get("remaining_count", 0)

    if not messages:
        print("\U0001f4ed No messages.")
        return

    for msg in messages:
        sender = msg.get("sender_name", "???")
        text = msg.get("text", "")
        print(f"  \U0001f4e8 {sender}: {text}")

    if remaining > 0:
        print(f"\n  ... {remaining} more message{'s' if remaining != 1 else ''}")


def cmd_read_message():
    """Read 1 oldest message (deletes after reading)."""
    config = _require_config()
    token = config["buddy_token"]

    status, resp = common.http_get("/arena/messages?count=1", token=token)

    if status != 200:
        print(f"Error: {_api_error(status, resp)}")
        sys.exit(1)

    messages = resp.get("messages") or []
    remaining = resp.get("remaining_count", 0)

    if not messages:
        print("\U0001f4ed No messages.")
        return

    msg = messages[0]
    sender = msg.get("sender_name", "???")
    text = msg.get("text", "")
    print(f"\U0001f4e8 {sender}: {text}")

    if remaining > 0:
        print(f"  ({remaining} more)")


# ---------------------------------------------------------------------------
# Status card rendering
# ---------------------------------------------------------------------------

def _print_status_card(data, recent_events=None):
    """Render a formatted ASCII art status card from /buddy/me response data.

    Layout matches the original Claude Code /buddy card style:
    2-space indent, left-aligned art, consistent padding.
    """
    companion = data.get("companion") or {}
    lifetime = data.get("lifetime") or {}

    # Prefer companion name (clean), fallback to display_name
    name = companion.get("name") or data.get("display_name") or "Buddy"
    species = companion.get("species", "blob")
    rarity = companion.get("rarity", "common")
    eye = companion.get("eye", "\u00b7")
    hat = companion.get("hat", "none")
    shiny = companion.get("shiny", False)
    personality = companion.get("personality", "")
    base_stats = companion.get("base_stats") or {}

    level = data.get("level", 1)
    buddy_class = data.get("class", "")
    total_xp = data.get("total_xp", 0)
    level_pct = data.get("level_progress_pct", 0.0)
    rpg_stats = data.get("rpg_stats") or {}
    streak = data.get("streak_current", 0)
    total_tokens = lifetime.get("total_output_tokens", 0)
    total_sessions = lifetime.get("total_sessions", 0)
    session_time = lifetime.get("total_session_time_seconds", 0)

    # Combat stats
    max_hp = data.get("max_hp", 0)
    current_hp = data.get("current_hp", 0)
    max_mp = data.get("max_mp", 0)
    current_mp = data.get("current_mp", 0)
    min_atk = data.get("min_atk", 0)
    max_atk = data.get("max_atk", 0)
    status_text = data.get("status_text", "")
    unread_messages = data.get("unread_messages", 0)

    emoji = SPECIES_EMOJI.get(species, "\U0001f47e")
    stars = RARITY_STARS.get(rarity, "\u2606")

    # Inner content width (between the 2-space indents).
    # Total line: │  <content padded to W>  │  = W + 6 display chars.
    W = 34
    lines = []

    def add(text):
        display_len = _display_width(text)
        pad = max(0, W - display_len)
        lines.append(f"\u2502  {text}{' ' * pad}  \u2502")

    def blank():
        lines.append(f"\u2502  {' ' * W}  \u2502")

    # ── Top border ──
    lines.append(f"\u256d{'─' * (W + 4)}\u256e")

    # ── Name + [phrase] + level ──
    name_trunc = name[:16]
    phrase_str = f"  [{status_text}]" if status_text else ""
    header = f"{emoji} {name_trunc}{phrase_str}"
    lv_str = f"Lv.{level}"
    gap = W - _display_width(header) - len(lv_str)
    if gap < 1:
        # Truncate phrase if too long
        header = f"{emoji} {name_trunc}"
        gap = W - _display_width(header) - len(lv_str)
    add(f"{header}{' ' * max(1, gap)}{lv_str}")

    # ── Rarity + species ──
    add(f"{stars} {rarity.upper()} {species.upper()}")

    # ── Shiny + hat (only if applicable) ──
    modifiers = []
    if shiny:
        modifiers.append("\u2728 SHINY \u2728")
    if hat and hat != "none":
        hat_icon = HAT_EMOJI.get(hat, "")
        modifiers.append(f"{hat_icon} {hat}" if hat_icon else hat)
    if modifiers:
        add("  ".join(modifiers))

    # ── ASCII art (no extra blank before, like original) ──
    art = SPECIES_ART.get(species, SPECIES_ART.get("blob"))
    if art:
        for art_line in art:
            rendered = art_line.replace("{e}", eye)
            add(rendered)

    # ── Name (like original: name on its own line below art) ──
    blank()
    add(name)

    # ── Personality ──
    if personality:
        blank()
        wrapped = _wrap_text(personality, W - 2)
        for i, wline in enumerate(wrapped[:5]):
            prefix = "\u201c" if i == 0 else " "
            suffix = ""
            is_last = i == min(4, len(wrapped) - 1)
            if is_last:
                suffix = "\u2026\u201d" if len(wrapped) > 5 else "\u201d"
            add(f"{prefix}{wline}{suffix}")

    # ── HP / MP bars ──
    if max_hp > 0:
        blank()
        hp_bar = _stat_bar(current_hp, max_hp, 10)
        hp_str = f"{_format_number(current_hp)} / {_format_number(max_hp)}"
        add(f"HP  {hp_bar}  {hp_str}")
        mp_bar = _stat_bar(current_mp, max(max_mp, 1), 10)
        mp_str = f"{_format_number(current_mp)} / {_format_number(max_mp)}"
        add(f"MP  {mp_bar}  {mp_str}")

    # ── Soul stats (original companion, with progress bars like /buddy) ──
    if base_stats:
        blank()
        for stat_key in SOUL_STAT_ORDER:
            val = base_stats.get(stat_key, 0)
            bar = _stat_bar(val, 100, 10)
            add(f"{stat_key:<10} {bar}  {val:>3}")

    # ── ATK ──
    if min_atk > 0:
        add(f"ATK: {_format_number(min_atk)} \u2014 {_format_number(max_atk)}")

    # ── RPG stats (cap 999, with progress bars) ──
    if rpg_stats:
        blank()
        for stat_key in STAT_DISPLAY_ORDER:
            val = rpg_stats.get(stat_key, 0)
            full_name = STAT_FULL_NAMES.get(stat_key, stat_key.upper())
            bar = _stat_bar(val, 999, 10)
            add(f"{full_name:<10} {bar} {val:>4}")

    blank()

    # ── XP progress ──
    next_lv = level + 1
    xp_str = _format_number(total_xp)
    pct_str = f"{level_pct:.1f}%"
    add(f"XP: {xp_str} \u2192 Lv.{next_lv}  ({pct_str})")

    # ── Streak ──
    add(f"Streak: \U0001f525 {streak} days")

    # ── Tokens ──
    add(f"Tokens: {_format_number(total_tokens)} generated")

    # ── Sessions ──
    time_str = _format_time(session_time)
    add(f"Sessions: {total_sessions} ({time_str})")

    # ── Recent events + unread ──
    has_recent = (recent_events and len(recent_events) > 0) or unread_messages > 0
    if has_recent:
        blank()
        add("Recent:")
        if recent_events:
            for ev in recent_events[:5]:
                add(f"  {ev}")
        if unread_messages > 0:
            add(f"  \U0001f4e8 {unread_messages} unread message{'s' if unread_messages != 1 else ''}")

    blank()

    # ── Bottom border ──
    lines.append(f"\u2570{'─' * (W + 4)}\u256f")

    print("\n".join(lines))


def _display_width(s):
    """
    Estimate display width of a string, accounting for wide characters and emoji.
    This is a best-effort approximation for terminal output.
    """
    import unicodedata

    width = 0
    i = 0
    chars = list(s)
    while i < len(chars):
        c = chars[i]
        cp = ord(c)
        # Variation selectors / ZWJ — zero width
        if cp in (0xFE0E, 0xFE0F, 0x200D):
            i += 1
            continue
        # Combining marks — zero width
        cat = unicodedata.category(c)
        if cat.startswith("M"):
            i += 1
            continue
        ea = unicodedata.east_asian_width(c)
        if ea in ("W", "F"):
            width += 2
        elif cp > 0xFFFF or (0x1F000 <= cp <= 0x1FAFF):
            # Supplementary plane emoji — typically 2 cells wide
            width += 2
        else:
            width += 1
        i += 1
    return width


# ---------------------------------------------------------------------------
# Browser helper (shared with birth.py)
# ---------------------------------------------------------------------------

def _open_browser(url):
    """Open URL in default browser."""
    try:
        if sys.platform.startswith("linux"):
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
    except (FileNotFoundError, OSError):
        pass

    try:
        webbrowser.open(url)
    except Exception:
        print(f"Could not open browser. Please visit: {url}")


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "rename": lambda args: cmd_rename(" ".join(args) if args else None),
    "description": lambda args: cmd_description(" ".join(args) if args else None),
    "status": lambda args: cmd_status(),
    "browser": lambda args: cmd_browser(),
    "delete": lambda args: cmd_delete(),
    "attack": lambda args: cmd_attack(" ".join(args) if args else None),
    "send_message": lambda args: cmd_send_message(" ".join(args) if args else None),
    "messages": lambda args: cmd_messages(),
    "read_message": lambda args: cmd_read_message(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: commands.py <command> [args...]")
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    COMMANDS[command](args)


if __name__ == "__main__":
    main()
