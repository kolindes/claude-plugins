---
description: Attack another buddy by name
argument-hint: <target name>
allowed-tools: ["Bash"]
---
Run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/commands.js" attack $ARGUMENTS`
Show the output. Then add a brief reaction in the user's language — comment on the damage dealt, whether the target survived, or if there was an error (cooldown, not found, etc). Keep it fun and short.
