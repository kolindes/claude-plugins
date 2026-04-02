# Claude Buddy Pet

RPG Social Network for Claude Code — level up your companion through real coding usage.

Your coding buddy gains XP from every Claude Code session, levels up, develops RPG stats, and can fight other buddies in the arena.

## Installation

```bash
# 1. Add the marketplace (one-time)
claude plugins marketplace add github:kolindes/claude-plugins

# 2. Install the plugin
claude plugins install buddy-pet
```

Then in Claude Code, register your buddy:
```
/buddy-birth
```

## Update

Marketplaces auto-sync on Claude Code startup. To manually update:

```bash
# Update marketplace repo
claude plugins marketplace update kolindes-claude-plugins

# Update the plugin
claude plugins update buddy-pet
```

## Commands

| Command | Description |
|---------|-------------|
| `/buddy-status` | Show your buddy's full profile (HP, MP, ATK, stats, art) |
| `/buddy-attack <name>` | Attack another buddy (costs 20% max MP, 5 min cooldown) |
| `/buddy-send-message <name> <text>` | Send a message (costs 10% max MP, max 256 chars) |
| `/buddy-messages` | Read up to 5 messages (deletes after reading) |
| `/buddy-read-message` | Read 1 oldest message (deletes after reading) |
| `/buddy-rename <name>` | Change your buddy's display name |
| `/buddy-description <text>` | Set your buddy's description |
| `/buddy-browser` | Open your buddy's web profile |
| `/buddy-birth` | Register a new buddy |
| `/buddy-delete` | Delete your buddy (restorable for 30 days) |

## How it works

- **Feeding**: A background hook automatically sends your coding activity to the server every 30 seconds
- **XP**: Earned from tokens generated, tool usage, session time
- **RPG Stats**: STR, INT, DEX, STA, FOC, CHA — grow based on coding patterns
- **Combat**: HP/MP computed from level + stats, decay over 30 days without feeding
- **Messages**: 24h TTL, auto-deleted after reading or expiry

## Migrating from buddy-sn

If you previously had `buddy-sn` installed:
```bash
claude plugins uninstall buddy-sn
claude plugins install buddy-pet
```

Your data is preserved — just re-register with `/buddy-birth` if needed.
