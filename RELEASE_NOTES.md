
# Rhodes Planner v0.6.0 — Publish Candidate

- Fixed Penguin Statistics export so it now exports Rhodes' **effective farming
  deficit**, not the original upgrade requirement.
- For every effective farm target, Penguin receives `need = have + amount_to_farm`.
  This preserves Reserve semantics and prevents Penguin from subtracting the
  user's depot a second time.
- Reserved T4/T5 chains now export their lower-tier farming targets to Penguin,
  matching the Rhodes Stage tab.
- Penguin export now respects passive base LMD/EXP credit as well.
- Added stronger account-data minimization: normalized local inventory keeps
  progression materials + EXP cards only.
- Added `THIRD_PARTY_NOTICES.md`, corrected Penguin Statistics data-license
  attribution, and clarified that the project is non-commercial where Penguin
  data is used.
- Added weekly `pip-audit` + `bandit` GitHub Actions and Dependabot configuration.

## Validation target

- Full pytest suite
- Python compile check
- static secret/private-file scan
- release archive check

# v0.5.1 hotfix

- Fixed Farming/Crafting runtime crash caused by missing `fmt_num` quantity formatter.
- Added a regression test for quantity formatting.

# Rhodes Planner v0.5.0

A release-candidate build focused on workflow polish before publishing.

## What changed

- Reserve on a T4/T5 material now means **farm its full crafting chain anew**.
  Owned lower-tier ingredients are intentionally ignored for that reserved
  requirement.
- Current-plan rows now have **Edit** and **Remove** actions.
- Penguin Statistics config is now **copy-first** with a one-click clipboard
  button instead of a download-first workflow.
- Planner/farming copy was tightened for a cleaner public-facing build.
- README and portfolio copy were rewritten to match the current product rather
  than earlier prototype architecture.

## Validation

- 33 automated tests passing
- Python syntax check passing
