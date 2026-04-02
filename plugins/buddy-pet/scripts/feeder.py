#!/usr/bin/env python3
"""
Feeder hook script for buddy-pet plugin.
Called by Claude Code hooks with mode: start, heartbeat, flush.

Reads JSONL transcript, extracts assistant events, sends feeding batches.
"""

import fcntl
import json
import math
import os
import sys
import time
import urllib.request

# Add scripts dir to path for common import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

HEARTBEAT_INTERVAL = 30  # seconds (30 for testing, 300 for prod)

LOG_FILE = os.path.join(common.PLUGIN_DATA, "feeder.log")
LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:3100")


def _log(msg):
    """Log to local file + push to Loki (best-effort)."""
    ts = time.strftime('%H:%M:%S')
    # Always write to local file
    try:
        os.makedirs(common.PLUGIN_DATA, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"{ts} {msg}\n")
    except OSError:
        pass
    # Push to Loki (fire-and-forget, never blocks feeder)
    try:
        ns = str(int(time.time() * 1e9))
        payload = json.dumps({
            "streams": [{
                "stream": {"service": "feeder", "job": "buddy-pet-plugin"},
                "values": [[ns, f"{ts} {msg}"]]
            }]
        }).encode("utf-8")
        req = urllib.request.Request(
            LOKI_URL + "/loki/api/v1/push",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Never fail the feeder because of logging


# ---------------------------------------------------------------------------
# Auto-birth: ensure buddy exists for current account
# ---------------------------------------------------------------------------


def _ensure_config():
    """Load config for current account. Auto-birth if missing. Returns config or None."""
    config = common.load_config()
    if config and config.get("buddy_token"):
        return config
    return _auto_birth()


def _auto_birth():
    """Auto-register buddy for the current account. Returns config or None."""
    user_id = common.get_user_id()
    if user_id == "anon":
        _log("auto-birth: userId=anon, skip")
        return None

    _log("auto-birth: registering buddy...")

    user_hash = common.compute_user_hash(user_id)
    instance_id = common.compute_instance_id()

    # Read companion (may be None if user hasn't hatched yet)
    companion = common.read_companion_data()
    birth_data = {
        "user_hash": user_hash,
        "instance_id": instance_id,
        "plugin_version": common.PLUGIN_VERSION,
    }
    if companion:
        birth_data["companion"] = {
            "name": companion.get("name", ""),
            "personality": companion.get("personality", ""),
            "hatched_at": companion.get("hatched_at", 0),
            "species": companion.get("species", ""),
            "rarity": companion.get("rarity", ""),
            "eye": companion.get("eye", ""),
            "hat": companion.get("hat", ""),
            "shiny": companion.get("shiny", False),
            "base_stats": companion.get("base_stats", {}),
        }
    else:
        # Minimal companion — backend will accept it
        birth_data["companion"] = {
            "name": "Buddy", "personality": "", "species": "blob",
            "rarity": "common", "eye": "o", "hat": "none", "shiny": False,
            "hatched_at": 0, "base_stats": {},
        }

    status, resp = common.http_post("/guild/buddy/birth", birth_data)

    if status not in (200, 201):
        _log(f"auto-birth: failed HTTP {status}: {resp}")
        return None

    token = resp.get("buddy_token", "")
    buddy_id = resp.get("buddy_id", "")
    if not token:
        _log(f"auto-birth: no token in response: {resp}")
        return None

    config = {
        "buddy_token": token,
        "buddy_id": buddy_id,
        "api_url": common.get_api_url(),
    }
    common.save_config(config)

    name = resp.get("buddy", {}).get("name", buddy_id[:8])
    _log(f"auto-birth: OK — {name} ({buddy_id})")
    return config


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    mode = sys.argv[1]
    _log(f"--- {mode} ---")

    if mode == "start":
        do_start()
    elif mode == "heartbeat":
        do_heartbeat()
    elif mode == "flush":
        do_flush()


# ---------------------------------------------------------------------------
# Mode: start
# ---------------------------------------------------------------------------


def do_start():
    """SessionStart: auto-birth if needed, retry pending reports."""
    config = _ensure_config()
    if not config:
        return

    # Read stdin hook input (contains session_id, transcript_path)
    _read_hook_input()

    # Submit pending reports
    submit_pending(config["buddy_token"])


# ---------------------------------------------------------------------------
# Mode: heartbeat
# ---------------------------------------------------------------------------


def do_heartbeat():
    """UserPromptSubmit: send feeding if interval since last send."""
    config = _ensure_config()
    if not config:
        return

    hook_input = _read_hook_input()
    if not hook_input:
        _log("heartbeat: no hook_input, skip")
        return

    state = common.load_state()

    # Check heartbeat interval
    now = time.time()
    elapsed = now - state.get("last_send_time", 0)
    if elapsed < HEARTBEAT_INTERVAL:
        _log(f"heartbeat: {elapsed:.0f}s < {HEARTBEAT_INTERVAL}s, skip")
        return

    _log(f"heartbeat: {elapsed:.0f}s elapsed, sending...")
    _send_events(config, hook_input, state)


# ---------------------------------------------------------------------------
# Mode: flush
# ---------------------------------------------------------------------------


def do_flush():
    """SessionEnd: send all remaining events (no time check)."""
    config = _ensure_config()
    if not config:
        return

    hook_input = _read_hook_input()
    if not hook_input:
        _log("flush: no hook_input, skip")
        return

    _log("flush: sending all remaining events")

    state = common.load_state()
    _send_events(config, hook_input, state)


# ---------------------------------------------------------------------------
# Core: read JSONL, extract events, send
# ---------------------------------------------------------------------------


def _send_events(config, hook_input, state):
    """Acquire lock, read JSONL, extract events, POST /feeding."""
    session_id = hook_input.get("session_id", "")
    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")

    if not transcript_path or not os.path.isfile(transcript_path):
        _log(f"send: no transcript at {transcript_path}")
        return

    # Acquire file lock (non-blocking)
    lock_fd = _acquire_lock()
    if lock_fd is None:
        _log("send: lock held by another process")
        return

    try:
        # Reload state under lock (may have changed)
        state = common.load_state()

        # Get session state
        sessions = state.get("sessions", {})
        session_state = sessions.get(session_id, {"offset": 0, "batch_seq": 0})
        offset = session_state.get("offset", 0)

        # Read JSONL from offset
        events, new_offset = _read_jsonl_events(transcript_path, offset)

        if not events:
            _log(f"send: no new events (offset={offset})")
            return

        # Check companion sync
        companion_sync = None
        current_companion_hash = common.companion_hash_string()
        if current_companion_hash and current_companion_hash != state.get("companion_hash", ""):
            companion_data = common.read_companion_data()
            if companion_data:
                companion_sync = companion_data
                _log("send: companion sync included (hash changed)")

        # Build payload
        batch_seq = int(time.time())
        payload = {
            "session_hash": common.compute_session_hash(session_id),
            "project_hash": common.compute_project_hash(cwd),
            "batch_seq": batch_seq,
            "plugin_version": common.PLUGIN_VERSION,
            "companion_sync": companion_sync,
            "events": events,
        }

        # POST /feeding
        _log(f"send: POST /feeding {len(events)} events, offset {offset}->{new_offset}")
        status, resp = common.http_post("/feeding", payload, token=config["buddy_token"])
        _log(f"send: HTTP {status} → {resp}")

        if status == 401:
            # Token invalid — re-register and retry once
            _log("send: 401 — token invalid, re-registering")
            common.delete_config()
            new_config = _auto_birth()
            if new_config:
                payload["session_hash"] = common.compute_session_hash(session_id)
                status, resp = common.http_post("/feeding", payload, token=new_config["buddy_token"])
                _log(f"send: retry HTTP {status} → {resp}")

        if status in (202, 409):
            # Success or duplicate — update state
            session_state["offset"] = new_offset
            session_state["batch_seq"] = batch_seq
            sessions[session_id] = session_state
            state["sessions"] = sessions
            state["last_send_time"] = time.time()
            if current_companion_hash:
                state["companion_hash"] = current_companion_hash
            common.save_state(state)
        elif status != 401:
            # Non-auth failure — save to pending for retry
            _log(f"send: HTTP {status} non-success, saving to pending")
            _save_pending(payload)

    finally:
        _release_lock(lock_fd)


def _read_jsonl_events(transcript_path, offset):
    """
    Read JSONL file from byte offset, extract assistant and compact_boundary events.
    Returns (events_list, new_byte_offset).
    """
    events = []

    try:
        with open(transcript_path, "rb") as f:
            f.seek(offset)
            raw = f.read()
            new_offset = offset + len(raw)
    except (IOError, OSError):
        return [], offset

    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        entry_type = entry.get("type")

        # Assistant messages with model response
        if entry_type == "assistant" and "message" in entry:
            event = _extract_assistant_event(entry)
            if event:
                events.append(event)

        # Compact boundary
        elif entry_type == "system" and entry.get("subtype") == "compact_boundary":
            event = _extract_compact_event(entry)
            if event:
                events.append(event)

    return events, new_offset


def _extract_assistant_event(entry):
    """Extract event fields from an assistant JSONL entry."""
    msg = entry.get("message", {})
    usage = msg.get("usage", {})
    content = msg.get("content", [])
    server_tool_use = usage.get("server_tool_use", {})

    # Parse timestamp: ISO 8601 to unix millis
    e_ts = _iso_to_millis(entry.get("timestamp", ""))
    if e_ts is None:
        return None

    # Content analysis
    c_types = []
    c_tu_n = []
    c_tu_ids = []
    c_ts = False

    for block in content:
        block_type = block.get("type", "")
        if block_type and block_type not in c_types:
            c_types.append(block_type)

        if block_type == "thinking":
            if block.get("signature"):
                c_ts = True

        elif block_type == "tool_use":
            tool_name = block.get("name", "")
            tool_id = block.get("id", "")
            if tool_name and tool_name not in c_tu_n:
                c_tu_n.append(tool_name)
            if tool_id:
                c_tu_ids.append(tool_id)

    # Build event with exact gateway field names
    event = {
        "e_ts": str(e_ts),
        "e_t": "assistant",
        "m_id": msg.get("id", ""),
        "r_id": entry.get("requestId", ""),
        "model": msg.get("model", ""),
        "u_ot": usage.get("output_tokens", 0),
        "u_it": usage.get("input_tokens", 0),
        "u_crt": usage.get("cache_read_input_tokens", 0),
        "u_cwt": usage.get("cache_creation_input_tokens", 0),
        "u_ws": server_tool_use.get("web_search_requests", 0),
        "c_types": c_types,
        "c_tu_n": c_tu_n,
        "c_tu_ids": c_tu_ids,
        "c_ts": c_ts,
        "stop": msg.get("stop_reason"),  # null, "end_turn", "tool_use" — keep as-is
    }

    return event


def _extract_compact_event(entry):
    """Extract event fields from a compact_boundary JSONL entry."""
    e_ts = _iso_to_millis(entry.get("timestamp", ""))
    if e_ts is None:
        return None

    metadata = entry.get("compactMetadata", {})

    event = {
        "e_ts": str(e_ts),
        "e_t": "compact",
        "compact_pre_tokens": metadata.get("preTokens", 0),
    }

    return event


def _iso_to_millis(iso_str):
    """Parse ISO 8601 timestamp to unix milliseconds."""
    if not iso_str:
        return None
    try:
        # Handle "2026-04-01T08:57:54.470Z" format
        # Strip trailing Z and parse
        s = iso_str.rstrip("Z")
        # Split date and time
        if "T" not in s:
            return None
        date_part, time_part = s.split("T", 1)
        year, month, day = date_part.split("-")

        # Handle fractional seconds
        if "." in time_part:
            time_main, frac = time_part.split(".", 1)
            # Pad or truncate frac to 3 digits (millis)
            frac = frac[:3].ljust(3, "0")
            millis_frac = int(frac)
        else:
            time_main = time_part
            millis_frac = 0

        hour, minute, second = time_main.split(":")

        import calendar
        import datetime

        dt = datetime.datetime(
            int(year), int(month), int(day),
            int(hour), int(minute), int(second),
            tzinfo=datetime.timezone.utc,
        )
        epoch_seconds = int(calendar.timegm(dt.timetuple()))
        return epoch_seconds * 1000 + millis_frac

    except (ValueError, IndexError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Pending reports
# ---------------------------------------------------------------------------


def submit_pending(token):
    """Retry sending pending reports from PENDING_DIR."""
    if not os.path.isdir(common.PENDING_DIR):
        return

    try:
        files = sorted(os.listdir(common.PENDING_DIR))
    except OSError:
        return

    pending_json = [f for f in files if f.endswith(".json")]
    if pending_json:
        _log(f"pending: {len(pending_json)} files to retry")

    for fname in pending_json:
        fpath = os.path.join(common.PENDING_DIR, fname)
        try:
            with open(fpath, "r") as f:
                payload = json.load(f)
        except (IOError, json.JSONDecodeError):
            continue

        status, _resp = common.http_post("/feeding", payload, token=token)
        if status in (202, 409):
            _log(f"pending: sent {fname} (HTTP {status})")
            # Sent or duplicate — remove
            try:
                os.remove(fpath)
            except OSError:
                pass
        else:
            _log(f"pending: retry failed {fname} (HTTP {status})")


def _save_pending(payload):
    """Save a failed payload to PENDING_DIR for later retry."""
    os.makedirs(common.PENDING_DIR, exist_ok=True)
    fname = "{:.0f}.json".format(time.time() * 1000)
    fpath = os.path.join(common.PENDING_DIR, fname)
    try:
        with open(fpath, "w") as f:
            json.dump(payload, f)
    except (IOError, OSError):
        pass


# ---------------------------------------------------------------------------
# File locking
# ---------------------------------------------------------------------------


def _acquire_lock():
    """Acquire exclusive file lock (non-blocking). Returns fd or None."""
    os.makedirs(common.PLUGIN_DATA, exist_ok=True)
    try:
        fd = os.open(common.LOCK_FILE, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (IOError, OSError):
        return None


def _release_lock(fd):
    """Release file lock and close fd."""
    if fd is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except (IOError, OSError):
            pass


# ---------------------------------------------------------------------------
# Hook stdin
# ---------------------------------------------------------------------------


def _read_hook_input():
    """Read JSON from stdin (piped by Claude Code hook system)."""
    try:
        raw = sys.stdin.read()
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


if __name__ == "__main__":
    main()
