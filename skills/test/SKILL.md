---
name: test
description: Fire a POPR test notification and run its health check.
disable-model-invocation: true
---
Run `"${CLAUDE_PLUGIN_ROOT}/bin/popr" doctor` and then `"${CLAUDE_PLUGIN_ROOT}/bin/popr" test` with the Bash tool. Summarise the doctor output in two sentences, call out anything marked MISSING or ⚠, and ask the user to click the banner.
