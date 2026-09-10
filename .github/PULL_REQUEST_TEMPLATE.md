## What and why

<!-- The diff shows what changed. Explain why it needed to. -->

## Checklist

- [ ] `tests/test.sh` is green
- [ ] `shellcheck bin/popr install.sh tests/test.sh "packaging/Install POPR.command"` is clean
- [ ] Behaviour changes have an assertion in `tests/test.sh`
- [ ] No new runtime dependency (`jq` and `terminal-notifier` are the whole list)
- [ ] Every code path in `bin/popr` still exits 0, so a hook can never break a turn
- [ ] `docs/DESIGN.md` updated if this changes the architecture or lifts a documented limitation
