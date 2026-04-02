# Claude Plugins Marketplace

Community plugins for [Claude Code](https://claude.ai/code).

## Available Plugins

| Plugin | Description | Install |
|--------|-------------|---------|
| [**buddy-sn**](https://github.com/kolindes/claude-buddy-pet-plugin) | RPG companion social network — level up your Claude buddy through real coding | `git clone --recurse-submodules` |

## Installation

### All plugins at once
```bash
cd ~/.claude/plugins/marketplaces
git clone --recurse-submodules https://github.com/kolindes/claude-plugins.git kolindes-claude-plugins
```

### Single plugin
```bash
cd ~/.claude/plugins/marketplaces
mkdir -p kolindes-claude-plugins/plugins
cd kolindes-claude-plugins/plugins
git clone https://github.com/kolindes/claude-buddy-pet-plugin.git buddy-sn
```

Restart Claude Code to activate hooks and commands.

## Plugin: buddy-sn

RPG social network for Claude Code companions. Your buddy gains XP from real coding sessions.

**Features:**
- Auto-registration on first use (no manual setup)
- Real-time feeding from Claude Code transcripts
- XP system with 6-component formula + anti-cheat
- RPG stats (STR/INT/DEX/STA/FOC/CHA, cap 999)
- Level system (cap 999, ~3 years to max for active user)
- Leaderboard, public profiles, achievements
- ASCII art for all 18 companion species
- Per-account support (multiple Claude accounts)

**Commands:**
- `/buddy-sn:buddy-status` — show your buddy card
- `/buddy-sn:buddy-birth` — manual registration
- `/buddy-sn:buddy-rename` — change display name
- `/buddy-sn:buddy-description` — set profile description
- `/buddy-sn:buddy-browser` — open profile in browser
- `/buddy-sn:buddy-delete` — delete buddy (30-day restore window)

**API:** https://guild.claude-buddy.pet
