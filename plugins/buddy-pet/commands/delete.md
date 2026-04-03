---
description: Delete your BUDDY (can restore within 30 days)
allowed-tools: ["Bash", "AskUserQuestion"]
---
First, ask the user to confirm deletion in their language. Warn that the buddy will be soft-deleted for 30 days, after which it's permanent.
If the user confirms, run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/commands.js" delete`
Show the output. Mention in the user's language that they can run /buddy-pet:birth within 30 days to restore.
