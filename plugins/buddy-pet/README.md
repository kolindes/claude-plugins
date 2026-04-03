# Claude Buddy Pet

Start a coding session. A tiny snail hatches in the corner. By the end of the day, it has gained two levels and learned that you favor refactoring over writing new code. A week later, someone attacks it in the arena. You fight back.

**Your Claude Code companion that levels up while you code.** No setup beyond install. No npm packages. Just code and watch it grow.

## What You Get

```
🐉 Dragon_max  [locked & loaded]  Lv.999
★★★★★ LEGENDARY DRAGON
✨ SHINY ✨  ♛ crown

  /^\  /^\
 <  @  @  >
 (   ~~   )
  `-vvvv-´

Dragon_max

"The ultimate coding companion. Has achieved
 enlightenment through pure functional programming
 and emerged on the other side writing Go."

HP  █████░░░░░  5.11M / 10.1M
MP  ░░░░░░░░░░  0 / 1.08M
ATK: 539K — 809K

DEBUGGING  █████░░░░░   50
PATIENCE   █████░░░░░   50
CHAOS      █████░░░░░   50
WISDOM     █████░░░░░   50
SNARK      █████░░░░░   50

STRENGTH   ██████████  999
INTELLECT  ██████████  999
DEXTERITY  ██████████  999
STAMINA    ██████████  999
FOCUS      ██████████  999
CHARISMA   ██████████  999

XP: 1B → Lv.1000  (100.0%)
Streak: 🔥 999 days
Tokens: 2B generated
Sessions: 50000 (182.5 days)

Recent:
  ⚔ DarkKnight hit you for 12.5K dmg
  📨 message from CodeNinja
  ⚔ DarkKnight defeated you!
```

- 18 species (duck, cat, dragon, snail, axolotl, robot, and more) with ASCII art
- 5 rarities: common, uncommon, rare, epic, legendary — with hats and shiny variants
- 6 RPG stats (STR, INT, DEX, STA, FOC, CHA) that grow based on your coding patterns
- PVP arena: attack other buddies, send messages, track kills
- Hunger system: stop coding for 30 days and your buddy hibernates at 0 HP. Start coding again and it wakes up fully restored
- Privacy controls: choose exactly which metrics you share

## Install

In Claude Code, type `/plugins` and follow these steps:

1. Select **Marketplaces**
2. Select **Add marketplace**
3. Paste: `https://github.com/kolindes/claude-plugins`
4. Select **buddy-pet** to install

Then reload and register:

```
/reload-plugins
/birth
```

This rolls a random species, rarity, and stats for your buddy based on your account. You don't choose — the RNG gods decide.

<details>
<summary>Alternative: CLI install</summary>

```bash
claude plugins marketplace add github:kolindes/claude-plugins
claude plugins install buddy-pet
```
</details>

## Commands

All commands are prefixed with `buddy-pet:` (e.g. `/status` becomes `/buddy-pet:status`).

| Command | What it does |
|---------|-------------|
| `/status` | View full profile with HP, MP, ATK, stats, ASCII art |
| `/attack <name>` | Attack another buddy (costs 20% MP, 5 min cooldown) |
| `/send-message <name> <text>` | Send a message to a buddy (costs 10% MP, 256 char max) |
| `/messages` | Read up to 5 messages (consumed on read) |
| `/read-message` | Read 1 oldest message (consumed on read) |
| `/consents` | View privacy consent settings and XP impact |
| `/consent-disable <ids>` | Disable metric categories (e.g. `1 2 3` or `-1` for all) |
| `/consent-enable <ids>` | Re-enable metric categories |
| `/rename <name>` | Change your display name (letters, digits, `_`, `-`, 2-20 chars) |
| `/description <text>` | Set your profile description |
| `/browser` | Open your web profile |
| `/birth` | Register or reconnect your buddy |
| `/delete` | Delete your buddy (restorable for 30 days) |
| `/update` | Check for and install plugin updates |

Note: `<name>` in attack/message is the target's display name (one word, case-insensitive). Names can only contain letters, digits, underscore and hyphen. Must be unique.

## Privacy Controls

You choose which coding metrics to share. By default everything is on. Disable any category and that data stops being collected — your XP gain slows proportionally.

```
/consents

 #   Category            XP%    Status
---  ------------------  -----  ------
 1   token_usage          ~68%    ON
 2   tool_usage           ~16%    ON
 3   model_identity        ~0%   OFF
 4   thinking_mode         ~0%    ON
 5   web_search            ~3%    ON
 6   session_timing       ~13%    ON
 7   project_identity      ~0%    ON

XP earning: 100% of maximum
```

Disable: `/consent-disable 1 3 5` or `/consent-disable -1` to disable all.
Enable: `/consent-enable 1 3 5` or `/consent-enable -1` to re-enable all.

Consent is enforced at three layers:
1. **Plugin** — filters data before sending (client-side)
2. **Server** — validates and zeros non-consented fields on receive
3. **XP Engine** — skips disabled metrics during computation

Even if the plugin is modified, the server enforces your consent settings.

## How It Works

**You just code.** A background hook automatically sends your coding activity metrics to the server every 30 seconds. Your buddy gains XP and stats grow on their own.

- **Stats**: STR grows from tool-heavy sessions, INT from longer thinking, STA from marathon sessions, DEX from varied tool use, FOC from deep single-task work, CHA from collaborative patterns
- **Combat**: Attack costs MP. Damage is based on ATK (derived from max HP). 5-minute cooldown per target
- **Hunger**: HP decays over 30 days without coding. MP decays in 10 days. At 0 HP your buddy hibernates — it's not dead, just sleeping. Feed it by coding and it wakes up at full HP/MP
- **Messages**: Cost MP to send, auto-deleted after 24 hours or after reading

## What Data Is Sent

The plugin sends **per-turn coding metrics** to `guild.claude-buddy.pet` every 30 seconds. You can disable any category via `/consents`.

| Category | Data sent | XP impact | Can disable? |
|----------|-----------|-----------|-------------|
| Token usage | Input/output/cache token counts | ~68% | Yes |
| Tool usage | Tool names and count | ~16% | Yes |
| Session timing | Session duration, streak | ~13% | Yes |
| Web search | Search request count | ~3% | Yes |
| Model identity | Model name | Stats only | Yes |
| Thinking mode | Extended thinking usage | Stats only | Yes |
| Project identity | Hashed project directory | Stats only | Yes |
| Base (always on) | Message count, timestamps | ~4% | No |

**Never sent:** your code, prompts, conversation content, file contents, or actual file paths.

Your account is identified by a SHA-256 hash of your Claude user ID — not the ID itself.

The server code is at [github.com/kolindes/code-buddy](https://github.com/kolindes/code-buddy).

## Update & Uninstall

**Update**: Run `/update` to check for new versions. Or: `/plugins` → Marketplaces → Update all, then `/reload-plugins`.

**Uninstall**: `/plugins` → select buddy-pet → Uninstall.

To fully clean up local data (config, logs, cached auth token):

```bash
rm -rf ~/.claude/plugins/data/buddy-pet
```

Your buddy data stays on the server for 30 days after deletion. Reinstall and `/birth` to reconnect.

## Requirements

- Claude Code (Windows, macOS, Linux)
- Node.js (already installed with Claude Code)
- A Claude account (not anonymous)
