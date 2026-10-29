# Automation opportunities

| Opportunity | Benefit | Safety risk | Dependency | Why deferred |
| --- | --- | --- | --- | --- |
| Coordinator continuation approval UI | Fewer manual authority updates | Could weaken explicit authority approval | Dedicated approval-policy task | C1.2 must preserve the existing human boundary. |
| Tab health/status polling | Faster detection of closed sessions | May confuse visible tab state with authority | iTerm2 host adapter | Tabs are intentionally non-authoritative. |
| Assisted handoff reminders | Less repeated coordination | Could become terminal keystroke injection | Explicit interaction policy | C1.2 only prints phrases for the human to use. |
