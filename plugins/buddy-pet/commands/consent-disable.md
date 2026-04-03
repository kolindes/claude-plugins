---
description: Disable consent categories (reduces XP gain)
argument-hint: <ids or -1 for all>
allowed-tools: ["Bash"]
---
Run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/commands.js" consent_disable $ARGUMENTS`
Show the output. Then explain in the user's language which metrics were disabled and how this affects XP gain. Warn that disabling metrics slows progression.
