---
description: Update buddy-pet plugin to the latest version
allowed-tools: ["Bash"]
---
Run these commands sequentially:
```bash
claude plugins marketplace update kolindes-claude-plugins && claude plugins uninstall buddy-pet && claude plugins install buddy-pet
```
Then tell the user: "Plugin updated. Run `/reload-plugins` to apply."
