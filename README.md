# Rhodes Planner

A local-first Arknights progression and farming planner that turns a player's
current account into an actionable upgrade plan.

> Import account state → choose operator targets → preserve any stash you want
> to keep → craft efficiently → farm the remaining T3 materials, LMD and EXP.

Rhodes Planner dynamically consumes current community game data and drop statistics, allowing new operators, materials, modules, and stages to be recognised automatically when upstream schemas remain compatible. 
Changes to upstream schemas or new progression mechanics may require a Rhodes Planner update.

## Why this exists

Arknights progression planning is usually split across several tools. Rhodes
Planner focuses on the account-aware workflow: what you already own, what you
want to build next, what can be crafted, and what still needs to be farmed.

I've been enjoying the game since it's release date. This toolkit is the culmination of my love-hate relationship with the game. 

## Highlights
- ArkPRTS full-account JSON import
- Persistent local profile with a dedicated **Nuke / Clear Profile** control
- Searchable operator tables with class, rarity and ownership filters
- Current operator state treated as a hard minimum
- Elite / level / skill / mastery / multi-module planning
- Multi-operator requirement aggregation
- Searchable advancement-material depot editor
- Per-resource **Reserve stash** policy
- T4/T5 requirements decomposed into T3 farming inputs
- Reserved T4/T5 requirements also reserve the full crafting chain
- Workshop crafting plan and LMD crafting cost
- Penguin Statistics farming data integration
- Explicit CE-6 / LS-6 run estimates
- Passive base LMD and T3 Battle Record production
- Penguin Statistics Planner config copy interoperability using the effective Rhodes farming deficit
- Local cache, diagnostics, tests and Windows launchers

## Quick start on Windows

If you already use Anaconda, run:

```text
run_windows_anaconda.bat
```

Otherwise:

```text
run_windows.bat
```

Rhodes Planner opens locally at:

```text
http://localhost:8501
```

The local launcher binds Streamlit to `127.0.0.1`.

## Data flow

```text
ARKprts / manual account state
            ↓
   persistent local profile
            ↓
     operator upgrade goals
            ↓
     total upgrade demand
            ↓
      stash reserve policy
            ↓
  craft-now + T3-first expansion
            ↓
    passive base production
            ↓
    stage/run recommendations
```

## Data sources and attribution

Rhodes Planner opens on a dedicated **Credits & Sources** page and ships with
[`CREDITS.md`](CREDITS.md).

Runtime data comes from community projects including:

- ArknightsAssets / ArknightsGamedata
- Penguin Statistics / ArkPlanner
- ARKprts / arkprtserver ecosystem exports
- community Arknights image repositories

Arknights and related game content remain the property of their respective
rights holders. Rhodes Planner is unofficial and unaffiliated.

## License and data-use boundary

Rhodes Planner's original source code is MIT-licensed. Runtime data/assets are
separate: Penguin Statistics API data is subject to **CC BY-NC 4.0**, while
Arknights game data/art remain subject to their upstream/rightsholder terms.
This repository does not bundle game-data snapshots or third-party image
assets. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

For that reason, treat this release as a **non-commercial fan/portfolio
project** unless you separately resolve the licenses/permissions for the data
sources used by your deployment.

## Privacy / security

Rhodes Planner is designed as a local-first personal toolkit.

- Raw ArkPRTS exports are parsed in memory and not persisted by Rhodes Planner.
- The saved local profile contains normalized roster, depot and plan data only.
- The local profile is not encrypted at rest.
- No account password or email verification code is requested.
- Public-data requests use fixed upstream endpoints.

See [`SECURITY.md`](SECURITY.md) for the current threat model.

## Tests

```bash
pytest -q
```

## Current limitations

- Farming is still an auditable expected-drop-per-sanity heuristic rather than
  a full global LP optimizer.
- Workshop byproducts are not credited.
- Event-shop economics and sanity-potion calendars are not modeled yet.
- Upstream community schemas can change and adapters may need maintenance.

## Acknowledgements

Rhodes Planner would not exist without the work of the Arknights community and the open-source projects that make tools like this possible.

A sincere thank you to:

- **Hypergryph and Yostar** for creating and publishing *Arknights*, the game that inspired this project in the first place.
- [**ArknightsAssets / ArknightsGamedata**](https://github.com/ArknightsAssets/ArknightsGamedata) for maintaining accessible structured game data used to keep operator, material, module, stage, and progression information current.
- [**Penguin Statistics**](https://penguin-stats.io/) and [**ArkPlanner**](https://github.com/penguin-statistics/ArkPlanner) for their extensive community-maintained drop data, farming statistics, planning concepts, and interoperability ecosystem.
- [**ArkPRTS**](https://github.com/thesadru/ArkPRTS) and [**arkprtserver**](https://github.com/ashleney/arkprtserver) for making detailed account-data export workflows possible, which became the foundation of Rhodes Planner's account-aware planning features.
- [**Arknight-Images by Aceship**](https://github.com/Aceship/Arknight-Images) and other community-maintained Arknights image repositories used for operator and material artwork in the interface.
- The broader **Arknights community**, whose guides, tools, experimentation, documentation, and shared knowledge continue to make projects like this possible.
- The maintainers and contributors behind [**Python**](https://www.python.org/), [**Streamlit**](https://streamlit.io/), and the many open-source libraries used throughout the project.
This project is an **unofficial, non-commercial fan project**.

All Arknights-related names, characters, artwork, game data, and other intellectual property belong to their respective rights holders.

To everyone whose work, data, documentation, tooling, and community knowledge helped make Rhodes Planner possible: **thank you.**

## Portfolio summary

This project demonstrates Python application development, API integration,
external-schema normalization, domain modeling, deterministic progression

## AI-Assisted Development
Rhodes Planner was developed using an AI-assisted development workflow. AI tools were used to help generate and refactor code, investigate bugs, design tests, and iterate on implementation.  
Project scope, feature requirements, UX decisions, testing scenarios, validation against real account data, and release decisions were directed and reviewed by the project author. Generated code was iteratively tested and corrected throughout development.
logic, local persistence, data-security design, caching, testing, and
optimization-oriented product design.
