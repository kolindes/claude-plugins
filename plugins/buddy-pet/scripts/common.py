"""
Shared utilities for buddy-pet plugin.
Config/state management, HTTP helpers, hash computation, companion reading.
Python 3.8+ stdlib only.
"""

import hashlib
import json
import os
import socket
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PLUGIN_DATA = os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    os.path.expanduser("~/.claude/plugins/data/buddy-pet"),
)

_LEGACY_CONFIG_FILE = os.path.join(PLUGIN_DATA, "config.json")
STATE_FILE = os.path.join(PLUGIN_DATA, "state.json")
LOCK_FILE = os.path.join(PLUGIN_DATA, ".lock")
PENDING_DIR = os.path.join(PLUGIN_DATA, "pending")

CLAUDE_CONFIG_FILE = os.path.expanduser("~/.claude.json")

# ---------------------------------------------------------------------------
# API URL
# ---------------------------------------------------------------------------

_DEFAULT_API_URL = "https://guild.claude-buddy.pet"


def get_api_url():
    """Return API URL from env, config, or default."""
    env_url = os.environ.get("BUDDY_API_URL")
    if env_url:
        return env_url.rstrip("/")
    cfg = load_config()
    if cfg and cfg.get("api_url"):
        return cfg["api_url"].rstrip("/")
    return _DEFAULT_API_URL


# ---------------------------------------------------------------------------
# Config — per-account: config_{user_hash_prefix}.json
# ---------------------------------------------------------------------------


def _user_hash_prefix():
    """Return first 8 chars of current user_hash for filename."""
    uid = get_user_id()
    if uid == "anon":
        return "anon"
    return compute_user_hash(uid)[:8]


def _config_file(prefix=None):
    """Return config file path for given user_hash prefix (or current account)."""
    if prefix is None:
        prefix = _user_hash_prefix()
    return os.path.join(PLUGIN_DATA, f"config_{prefix}.json")


def _migrate_legacy_config():
    """Remove old config.json — cannot reliably determine which account it belongs to.
    Auto-birth will create the correct per-account config on next heartbeat."""
    if not os.path.isfile(_LEGACY_CONFIG_FILE):
        return
    try:
        os.remove(_LEGACY_CONFIG_FILE)
    except OSError:
        pass


def load_config():
    """Load config for the current account. Returns dict or None."""
    _migrate_legacy_config()
    path = _config_file()
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_config(config):
    """Save config for the current account."""
    config["user_hash_prefix"] = _user_hash_prefix()
    os.makedirs(PLUGIN_DATA, exist_ok=True)
    path = _config_file()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, path)


def delete_config():
    """Delete config for the current account (e.g., on 401)."""
    path = _config_file()
    try:
        os.remove(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# State (last_send_time, companion_hash, sessions: {sid: {offset, batch_seq}})
# ---------------------------------------------------------------------------

_DEFAULT_STATE = {
    "last_send_time": 0,
    "companion_hash": "",
    "sessions": {},
}


def load_state():
    """Load state.json. Returns dict with defaults for missing keys."""
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    # Merge defaults
    for k, v in _DEFAULT_STATE.items():
        if k not in state:
            state[k] = v if not isinstance(v, dict) else dict(v)
    return state


def save_state(state):
    """Save state.json atomically."""
    os.makedirs(PLUGIN_DATA, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


# ---------------------------------------------------------------------------
# HTTP helpers (urllib only, no requests)
# ---------------------------------------------------------------------------


def _make_request(method, path, data=None, token=None):
    """
    Make an HTTP request. Returns (status_code, response_dict).
    On network/HTTP errors returns (0, {"error": "..."}).
    """
    url = get_api_url() + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "BuddyToken " + token

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        # Bypass proxy for API requests — avoids SSL issues with local HTTP proxies.
        no_proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(no_proxy_handler)
        resp = opener.open(req, timeout=8)
        resp_body = resp.read().decode("utf-8")
        try:
            return resp.status, json.loads(resp_body)
        except json.JSONDecodeError:
            return resp.status, {"raw": resp_body}
    except urllib.error.HTTPError as e:
        resp_body = ""
        try:
            resp_body = e.read().decode("utf-8")
        except Exception:
            pass
        try:
            return e.code, json.loads(resp_body)
        except (json.JSONDecodeError, ValueError):
            return e.code, {"error": resp_body or str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def http_post(path, data, token=None):
    """POST JSON to API. Returns (status_code, response_dict)."""
    return _make_request("POST", path, data=data, token=token)


def http_get(path, token=None):
    """GET from API. Returns (status_code, response_dict)."""
    return _make_request("GET", path, token=token)


def http_patch(path, data, token=None):
    """PATCH JSON to API. Returns (status_code, response_dict)."""
    return _make_request("PATCH", path, data=data, token=token)


# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------

_BUDDY_SALT = "buddy-pet-salt"


def compute_token_hash(token):
    """SHA-256 hex hash of a token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def compute_instance_id():
    """SHA-256 of hostname + username + plugin_data_dir."""
    hostname = socket.gethostname()
    username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    raw = hostname + username + PLUGIN_DATA
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_user_hash(user_id):
    """SHA-256 of userId + salt."""
    return hashlib.sha256((user_id + _BUDDY_SALT).encode("utf-8")).hexdigest()


def compute_project_hash(cwd):
    """SHA-256 of working directory path."""
    return "sha256:" + hashlib.sha256(cwd.encode("utf-8")).hexdigest()


def compute_session_hash(session_id):
    """SHA-256 of session_id."""
    return "sha256:" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Companion reading from ~/.claude.json
# ---------------------------------------------------------------------------


def read_claude_config():
    """Read the full ~/.claude.json. Returns dict or None."""
    try:
        with open(CLAUDE_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_user_id():
    """Get userId from ~/.claude.json (oauthAccount.accountUuid or userID)."""
    cfg = read_claude_config()
    if not cfg:
        return "anon"
    oauth = cfg.get("oauthAccount", {})
    return oauth.get("accountUuid") or cfg.get("userID") or "anon"


def read_companion_data():
    """
    Read companion data from ~/.claude.json.
    Returns dict with companion soul + computed bones, or None.
    """
    cfg = read_claude_config()
    if not cfg:
        return None
    companion = cfg.get("companion")
    if not companion:
        return None

    user_id = get_user_id()
    bones = compute_bones(user_id)

    result = {
        "name": companion.get("name", ""),
        "personality": companion.get("personality", ""),
        "hatched_at": companion.get("hatchedAt", 0),
    }
    result.update(bones)
    result["user_hash"] = compute_user_hash(user_id)
    return result


def companion_hash_string():
    """Return a hash of the current companion state for change detection."""
    data = read_companion_data()
    if not data:
        return ""
    # Hash the serialized companion data
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Mulberry32 PRNG (ported from companion.ts)
# ---------------------------------------------------------------------------

# Must match Claude Code exactly: same salt, same arrays, same algorithm.
_PRNG_SALT = "friend-2026-401"

SPECIES = [
    "duck", "goose", "blob", "cat", "dragon", "octopus", "owl", "penguin",
    "turtle", "snail", "ghost", "axolotl", "capybara", "cactus", "robot",
    "rabbit", "mushroom", "chonk",
]

EYES = ["·", "\u2726", "\u00d7", "\u25c9", "@", "\u00b0"]

HATS = ["none", "crown", "tophat", "propeller", "halo", "wizard", "beanie", "tinyduck"]

STAT_NAMES = ["DEBUGGING", "PATIENCE", "CHAOS", "WISDOM", "SNARK"]

RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]

RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "epic": 4,
    "legendary": 1,
}

_RARITY_FLOOR = {
    "common": 5,
    "uncommon": 15,
    "rare": 25,
    "epic": 35,
    "legendary": 50,
}

_MASK32 = 0xFFFFFFFF


def _to_int32(x):
    """Truncate to signed 32-bit integer (like JS |0)."""
    import ctypes
    return ctypes.c_int32(x & _MASK32).value


def _to_uint32(x):
    """Truncate to unsigned 32-bit integer (like JS >>> 0)."""
    return x & _MASK32


def _math_imul(a, b):
    """JS Math.imul: lower 32 bits of a*b as signed int32."""
    return _to_int32(a * b)


def _hash_string(s):
    """FNV-1a 32-bit hash, matching the TypeScript hashString()."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = _math_imul(h, 16777619)
    return _to_uint32(h)


def _mulberry32(seed):
    """Mulberry32 PRNG generator, matching TypeScript exactly.

    JS source:
        a |= 0
        a = (a + 0x6d2b79f5) | 0
        let t = Math.imul(a ^ (a >>> 15), 1 | a)
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    """
    a = _to_uint32(seed)

    def next_val():
        nonlocal a
        a = _to_int32(a)
        a = _to_int32(a + 0x6D2B79F5)
        t = _math_imul(_to_int32(a) ^ (_to_uint32(a) >> 15), _to_int32(1 | a))
        t = _to_int32(
            _to_int32(
                t + _math_imul(_to_int32(t) ^ (_to_uint32(t) >> 7), _to_int32(61 | t))
            ) ^ t
        )
        return _to_uint32(t ^ (_to_uint32(t) >> 14)) / 4294967296.0

    return next_val


def _pick(rng, arr):
    """Pick a random element from arr using rng, matching TS Math.floor(rng() * len)."""
    import math
    return arr[math.floor(rng() * len(arr))]


def _roll_rarity(rng):
    """Roll a rarity using weighted distribution."""
    total = sum(RARITY_WEIGHTS.values())
    roll = rng() * total
    for rarity in RARITIES:
        roll -= RARITY_WEIGHTS[rarity]
        if roll < 0:
            return rarity
    return "common"


def _roll_stats(rng, rarity):
    """Roll stats with one peak, one dump, rest scattered. Rarity bumps floor."""
    import math
    floor = _RARITY_FLOOR[rarity]
    peak = _pick(rng, STAT_NAMES)
    dump = _pick(rng, STAT_NAMES)
    while dump == peak:
        dump = _pick(rng, STAT_NAMES)

    stats = {}
    for name in STAT_NAMES:
        if name == peak:
            stats[name] = min(100, floor + 50 + math.floor(rng() * 30))
        elif name == dump:
            stats[name] = max(1, floor - 10 + math.floor(rng() * 15))
        else:
            stats[name] = floor + math.floor(rng() * 40)
    return stats


def compute_bones(user_id):
    """
    Compute companion bones from userId, matching Claude Code's roll() exactly.
    Returns dict with: rarity, species, eye, hat, shiny, base_stats.
    """
    key = user_id + _PRNG_SALT
    rng = _mulberry32(_hash_string(key))

    rarity = _roll_rarity(rng)
    species = _pick(rng, SPECIES)
    eye = _pick(rng, EYES)
    hat = "none" if rarity == "common" else _pick(rng, HATS)
    shiny = rng() < 0.01
    stats = _roll_stats(rng, rarity)

    return {
        "rarity": rarity,
        "species": species,
        "eye": eye,
        "hat": hat,
        "shiny": shiny,
        "base_stats": stats,
    }


# ---------------------------------------------------------------------------
# Plugin version
# ---------------------------------------------------------------------------

PLUGIN_VERSION = "1.0.0"
