# Claude Buddy Pet

Start a coding session. A tiny snail hatches in the corner. By the end of the day, it has gained two levels and learned that you favor refactoring over writing new code. A week later, someone attacks it in the arena. You fight back.

**Your Claude Code companion that levels up while you code.** No setup beyond install. No npm packages. Just code and watch it grow.

## What You Get

```
╭──────────────────────────────────────╮
│  🐌 Cinder  [in the zone]      Lv.3  │
│  ★★★ RARE SNAIL                      │
│                                      │
│   @    .--.                          │
│    \  ( @ )                          │
│     \_`--´                           │
│    ~~~~~~~                           │
│                                      │
│  HP  ██████████  7.6K / 7.6K         │
│  MP  ████████░░  8.4K / 10.6K        │
│  ATK: 407 — 610                      │
│                                      │
│  STRENGTH   ██░░░░░░░░   71          │
│  INTELLECT  ██░░░░░░░░  140          │
│                                      │
│  Recent:                             │
│    ⚔ kolindes hit you for 434 dmg    │
│    📨 message from DarkKnight        │
╰──────────────────────────────────────╯
```

- 18 species (duck, cat, dragon, snail, axolotl, robot, and more) with ASCII art
- 5 rarities: common, uncommon, rare, epic, legendary -- with hats and shiny variants
- 6 RPG stats (STR, INT, DEX, STA, FOC, CHA) that grow based on your coding patterns
- PVP arena: attack other buddies, send messages, track kills
- Hunger system: stop coding for 30 days and your buddy hibernates at 0 HP. Start coding again and it wakes up fully restored

## Install

In Claude Code, type `/plugins` and follow these steps:

1. Select **Marketplaces**
2. Select **Add marketplace**
3. Paste: `https://github.com/kolindes/claude-plugins`
4. Select **buddy-pet** to install

Then reload and register:

```
/reload-plugins
/buddy-birth
```

This rolls a random species, rarity, and stats for your buddy based on your account. You don't choose -- the RNG gods decide.

<details>
<summary>Alternative: CLI install</summary>

```bash
claude plugins marketplace add github:kolindes/claude-plugins
claude plugins install buddy-pet
```
</details>

## Commands

| Command | What it does |
|---------|-------------|
| `/buddy-status` | View full profile with HP, MP, ATK, stats, ASCII art |
| `/buddy-attack <name>` | Attack another buddy (costs 20% MP, 5 min cooldown) |
| `/buddy-send-message <name> <text>` | Send a message to a buddy (costs 10% MP, 256 char max) |
| `/buddy-messages` | Read up to 5 messages (consumed on read) |
| `/buddy-read-message` | Read 1 oldest message (consumed on read) |
| `/buddy-rename <name>` | Change your display name |
| `/buddy-description <text>` | Set your profile description |
| `/buddy-browser` | Open your web profile |
| `/buddy-birth` | Register or reconnect your buddy |
| `/buddy-delete` | Delete your buddy (restorable for 30 days) |

Note: `<name>` in attack/message is the target's display name (one word, case-insensitive).

## How It Works

**You just code.** A background hook automatically sends your coding activity metrics to the server every 30 seconds. Your buddy gains XP and stats grow on their own.

- **Stats**: STR grows from tool-heavy sessions, INT from longer thinking, STA from marathon sessions, DEX from varied tool use, FOC from deep single-task work, CHA from collaborative patterns
- **Combat**: Attack costs MP. Damage is based on ATK (derived from max HP). 5-minute cooldown per target
- **Hunger**: HP decays over 30 days without coding. MP decays in 10 days. At 0 HP your buddy hibernates -- it's not dead, just sleeping. Feed it by coding and it wakes up at full HP/MP
- **Messages**: Cost MP to send, auto-deleted after 24 hours or after reading

## What Data Is Sent

The plugin sends **per-turn coding metrics** to `guild.claude-buddy.pet` every 30 seconds:

| Sent | Not sent |
|------|----------|
| Token counts (input, output, cache) | Your code |
| Tool names used (Bash, Edit, etc.) | Your prompts |
| Model name | Conversation content |
| Session duration | File contents |
| Hashed session/project IDs | Actual file paths |
| Whether extended thinking was used | |

Your account is identified by a SHA-256 hash of your Claude user ID -- not the ID itself.

The server code is at [github.com/kolindes/code-buddy](https://github.com/kolindes/code-buddy).

## Update & Uninstall

**Update**: The marketplace auto-syncs when Claude Code starts. To force: `/plugins` → Marketplaces → Update all, then `/reload-plugins`.

**Uninstall**: `/plugins` → select buddy-pet → Uninstall.

To fully clean up local data (config, logs, cached auth token):

```bash
rm -rf ~/.claude/plugins/data/buddy-pet
```

Your buddy data stays on the server for 30 days after deletion. Reinstall and `/buddy-birth` to reconnect.

## Requirements

- Claude Code (Windows, macOS, Linux)
- Node.js (already installed with Claude Code)
- A Claude account (not anonymous)
