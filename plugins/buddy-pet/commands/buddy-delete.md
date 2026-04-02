---
description: Delete your BUDDY (can restore within 30 days)
allowed-tools: ["Bash", "AskUserQuestion"]
---
DANGER ZONE: This will delete the user's BUDDY.

First, ask the user to confirm: "Are you sure you want to delete your BUDDY? You have 30 days to restore via /buddy-birth."

If confirmed, run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/commands.py" delete`
Show the output.

If the user does not confirm, do not run the command.
