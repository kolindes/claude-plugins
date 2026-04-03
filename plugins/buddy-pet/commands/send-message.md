---
description: Send a message to another buddy (first word = target name, rest = message)
argument-hint: <target_name> <message text>
allowed-tools: ["Bash"]
---
Run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/commands.js" send_message $ARGUMENTS`
Show the output. Add a short confirmation in the user's language about the message being sent and MP cost.
