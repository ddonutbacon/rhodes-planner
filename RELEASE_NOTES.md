# Rhodes Planner v0.8.0

## Main changes

- Reworked the UI around a fast **Home → Account → Planner → Farming** workflow.
- Added an Arknights-style visual operator browser with live search plus class and sub-class filters.
- Operator browser uses an internal scroll area so the planner remains close at hand.
- Imported account state is now a starting baseline rather than a hard planner minimum.
- Added editable per-goal starting states and manual account maintenance.
- Added Active/paused goals, priority reordering and Undo after goal deletion.
- Added exact reserve quantities for materials, LMD and EXP.
- Added ArkPRTS import verification and LMD raw-vs-parsed auditing.
- Added import-diff review and optional preservation of manual account overrides.
- Added quick target/mastery presets and previous-target reuse.
- Reworked Farming into button-style **Reserve → Crafting → Stages → Summary** navigation.
- Farming tables now use icons and material/resource names instead of raw item IDs.
- Battle Record labels explicitly identify T1/T2/T3/T4 tiers.
- Passive RIIC production is explicitly modelled as up to **T3 Tactical Battle Records**.
- Added Chip Catalyst acquisition routing through Purchase Certificates and AP farming.
- Summary provides a concise final stage/run/sanity checklist.
- Penguin Statistics configuration can be copied directly or downloaded.
- Hosted profiles are browser-local by default; raw ArkPRTS uploads are not intentionally persisted.
- Removed portable-distribution workflow from the recommended release path.

## Deployment

Streamlit entry point:

`app/main.py`

Dependencies:

`requirements.txt`


## RC2 polish

- Removed the user-facing Diagnostics page.
- Simplified Home to a concise functional overview.
- Removed filesystem profile paths from the UI.
- Replaced Quick Material Edit with a scrollable inventory table containing icon, item name, tier and directly editable owned quantity.
- Added material search and tier filtering.


## Final account inventory polish

- Replaced the generic material data table with an Arknights-style six-column inventory grid.
- Removed material tier classification and tier filtering.
- Retained fast name search.
- Inventory follows the supplied in-game depot order from left to right, then top to bottom.
- LMD, Purchase Certificates and all four Battle Record tiers appear at the top of the same inventory view.
- Quantities are edited directly on each item card.
