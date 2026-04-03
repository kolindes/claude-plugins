---
description: Send a message to another buddy (first word = target name, rest = message)
argument-hint: <target_name> <message text>
allowed-tools: ["Bash"]
---
Run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/commands.js" send_message $ARGUMENTS`
Show the output exactly as printed. Do not reformat or wrap in a code block.
