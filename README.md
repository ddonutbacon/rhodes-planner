# Rhodes Planner

**A local-first, account-aware Arknights progression, crafting and farming planner.**

> Import your account → choose who you want to build → preserve the materials you want to keep → craft what you can → farm what is actually missing.

Rhodes Planner is an unofficial, non-commercial fan project built with Python and Streamlit.

It started from my own love-hate relationship with Arknights.

The idea eventually became simple:

**Take what I already own, understand what I want to build next, account for what can be crafted, preserve what I don't want to spend, and tell me what I actually still need to farm.**

---

## Why this exists

Arknights progression planning is usually spread across several different tools.

One tool tells you operator materials. Another helps with farming efficiency. Another may know your inventory. Then there are spreadsheets, browser tabs, calculators, and the inevitable moment where you realize you already had enough T4 material to craft what you just farmed.

Rhodes Planner tries to connect those pieces into one account-aware workflow:

```text
What do I already own?
        ↓
Who do I want to build?
        ↓
What does that upgrade actually require?
        ↓
What can I craft from my current inventory?
        ↓
What materials do I want to reserve?
        ↓
What is genuinely missing?
        ↓
Where should I farm it?
```

It is intended primarily as a personal planning tool, but I also built it as a software-development project: something I could keep testing against my own account, break, debug, rethink, and gradually make more reliable.

---

# v0.7.3

v0.7.3 expands Rhodes Planner from a current-account farming calculator into a more complete progression planner, including preparation for operators and materials that have not yet reached the EN server.

### Highlights

- **ArkPRTS full-account JSON import**
- Persistent local profile
- Searchable operator planning
- Elite, level, skill, mastery and module progression
- Per-operator requirement breakdowns
- Combined multi-operator material totals
- Reserve-aware inventory handling
- Crafting-aware deficit calculation
- **Dualchip factory crafting**
  - 2 matching Chip Packs + 1 Chip Catalyst correctly satisfy 1 class Dualchip before farming deficits are created
- T4/T5 requirement decomposition into lower-tier crafting inputs
- T3-first farming expansion
- Workshop crafting plan and LMD crafting cost
- Penguin Statistics farming integration
- LMD and EXP stage planning
- Passive base-production planning
- Penguin Statistics Planner-config export
- **CN-complete planner catalog**
- Future CN-only operator progression support
- Future-material awareness
- English display names for CN-only operators/materials where community terminology is available
- Dynamic farming availability from Penguin Statistics
- Portable Windows deployment
- Root-folder-name-independent launcher
- Automatic local-port fallback when port 8501 is already occupied

---

## Quick start

### Recommended: Portable Windows release

For most Windows users, this is the easiest option.

1. Download the latest **portable Windows ZIP** from GitHub Releases.
2. Extract the complete folder anywhere you want.
3. The extracted folder may be renamed or moved.
4. Double-click:

```text
Rhodes Planner.bat
```

5. Rhodes Planner starts locally and opens in your browser.

The launcher prefers:

```text
127.0.0.1:8501
```

If port `8501` is already in use, Rhodes automatically looks for another available local port.

The portable release includes its own Python runtime.

You do **not** need to install Python, pip, Conda or Streamlit globally.

---

## Developer installation

Clone the repository and create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Run Rhodes Planner:

```powershell
python -m streamlit run app\main.py --server.address 127.0.0.1
```

---

## How the planner works

At a high level:

```text
ARKprts / manual account state
            ↓
      local profile
            ↓
    operator upgrade goals
            ↓
   total material demand
            ↓
      reserve policy
            ↓
 currently owned materials
            ↓
    available crafting
            ↓
 effective farming deficit
            ↓
  stage/run recommendations
```

The important part is that Rhodes does not treat every upgrade requirement as something that must immediately be farmed.

It first considers:

- what you already own,
- what you want to preserve,
- what can be crafted,
- what higher-tier materials can be decomposed into crafting requirements,
- and what materials actually remain missing afterward.

---


## Inventory and reserve logic

Your current inventory is not automatically treated as fully disposable.

Rhodes supports a **reserve stash** policy so you can tell the planner:

> I technically own this material, but I do not want this amount consumed by the current plan.

That reserve is incorporated before Rhodes calculates the effective farming deficit.

Higher-tier reserves also matter.

If a T4 or T5 material is being preserved, Rhodes accounts for the lower-tier materials required to craft it instead of accidentally consuming its crafting chain elsewhere.

---

## Crafting

Rhodes attempts to use available crafting opportunities before recommending unnecessary farming.

This includes:

- workshop material crafting,
- high-tier material decomposition,
- crafting LMD cost,
- lower-tier dependency expansion,
- class Dual chip production.

For example:

```text
2 matching Chip Packs
+ 1 Chip Catalyst
= 1 class Dual chip
```

If those inputs already exist in the account inventory, Rhodes can satisfy the Dual chip requirement before creating a farming deficit.

---

## Farming recommendations

Rhodes uses Penguin Statistics data to identify available farming sources.

The planner focuses on the effective deficit after inventory, reserve and crafting logic have been applied.

Its farming model is intentionally auditable rather than pretending to solve every possible optimisation problem.

Current behaviour includes:

- material stage recommendations,
- expected-drop-based efficiency handling,
- CE-stage LMD planning,
- LS-stage EXP planning,
- T3-first expansion for higher-tier materials,
- dynamic recognition of newly reported drops.

---

## Account import

Rhodes Planner can import a user-supplied **ArkPRTS full-account JSON export**.

The imported account state can provide information such as:

- owned operators,
- operator progression,
- modules,
- skills/masteries,
- material inventory.

The imported file is used to normalise the planner state rather than becoming a permanent copy of the raw account export.

---

## Privacy and security

Rhodes Planner is designed as a **local-first personal toolkit**.

The application runs locally through Streamlit and binds to:

```text
127.0.0.1
```

Raw ArkPRTS account exports are parsed in memory and are not intentionally persisted by Rhodes Planner.

The saved local profile contains normalised planner state rather than game-login credentials.

The profile is stored locally as plaintext and is **not encrypted at rest**.

Rhodes Planner does not request:

- game-account passwords,
- email verification codes,
- authentication tokens.

A **Nuke / Clear Profile** control is available for removing the saved local profile.

For the current threat model and implementation limitations, see:

[`SECURITY.md`](SECURITY.md)

---

## Data sources

Rhodes Planner relies on public and community-maintained Arknights resources.

Runtime data and interoperability include projects such as:

- [ArknightsAssets / ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata)
- [Penguin Statistics](https://penguin-stats.io/)
- [ArkPRTS](https://github.com/ashleney/ArkPRTS)
- the wider ArkPRTS / arkprtserver ecosystem
- community-maintained image repositories

Rhodes retrieves community data at runtime rather than bundling complete game-data snapshots into the repository.

Arknights and its related game content remain the property of their respective rights holders.

Rhodes Planner is unofficial and unaffiliated with Hypergryph or Yostar.

See:

- [`CREDITS.md`](CREDITS.md)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

for fuller attribution and license boundaries.

---

## Tests

Run the regression suite with:

```powershell
python -m pytest
```

The test suite covers areas including:

- progression calculations,
- crafting behavior,
- Dualchip crafting,
- operator advancement,
- future-content handling,
- localization,
- ArkPRTS parsing,
- profile behaviour,
- security regressions,
- launcher portability.

I use regression tests heavily because Rhodes is the kind of project where fixing one edge case can very easily break another calculation somewhere else.

---

## Current limitations

Rhodes Planner is still evolving.

Some current limitations include:

- farming recommendations use an auditable expected-drop / efficiency model rather than a complete global LP optimiser,
- workshop byproducts are not currently credited,
- event-shop economics are not fully modelled,
- sanity-potion calendars are not modelled,
- upstream community APIs and schemas can change,
- future-content data naturally depends on what has already been published upstream.

There will probably always be another edge case. Arknights is very good at producing them.

---

## Portable build

The repository includes:

```text
build_portable_release.ps1
```

The builder creates a self-contained Windows package using a compatible portable Python runtime.

It does not depend on the final application folder being called `portable`.

A portable installation can therefore live somewhere like:

```text
C:\RhodesPlanner\
D:\Games\Arknights Tools\
E:\Portable Apps\Rhodes Planner\
```

or under essentially any other folder name.

The launcher resolves application paths relative to its own location rather than relying on the current command-line working directory.

---

## Portfolio / development perspective

Rhodes Planner is also a personal software-development project.

It has given me a practical environment for working with:

- Python application development,
- Streamlit UI development,
- external APIs,
- schema normalization,
- domain modelling,
- deterministic progression calculations,
- local persistence,
- caching,
- security/privacy decisions,
- automated testing,
- Windows portable deployment,
- debugging against real user/account data,
- and optimisation-oriented product design.

More importantly, it has been developed around an actual problem I personally wanted solved.

That makes it a much better learning project for me than building an application only because a tutorial said I should.

---

## AI-assisted development

Rhodes Planner was developed through an **AI-assisted iterative development workflow**.

AI tools were used extensively for:

- implementation,
- refactoring,
- debugging,
- investigating unexpected behaviour,
- generating and expanding regression tests,
- reviewing edge cases,
- documentation.

**OpenAI's ChatGPT** has been the primary implementation, debugging and testing partner during development.

That does not mean the project was produced from a single prompt and accepted as-is.

Product direction, feature requirements, UX decisions, planner behaviour, testing scenarios, real-account validation, privacy/security decisions and release decisions were directed and reviewed by me as the project author.

Generated implementations were repeatedly tested against actual planner behaviour, corrected when they failed, and changed when the resulting product did not behave the way I wanted.

AI is part of how this project was built.

The decisions about what Rhodes Planner should actually become are mine.

---

## License

Rhodes Planner's original application code is released under the:

[MIT License](LICENSE)

Runtime game data, community statistics, images and Arknights intellectual property are separate from the Rhodes Planner source-code license and retain their respective upstream/rights holder terms.

For that reason, Rhodes Planner should be treated as a **non-commercial fan and portfolio project** unless the necessary rights and licenses for a different use are separately established.

---

## Acknowledgements

Rhodes Planner stands on a large amount of work produced by the Arknights community.

Sincere thanks to:

- **Hypergryph and Yostar**
- [ArknightsAssets / ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata)
- [Penguin Statistics](https://penguin-stats.io/)
- [ArkPlanner](https://github.com/penguin-statistics/ArkPlanner)
- [ArkPRTS](https://github.com/ashleney/ArkPRTS)
- arkprtserver and the broader ArkPRTS ecosystem
- [imivi's Arknights Pulls Calculator](https://imivi.github.io/arknights-pulls-calculator/)
- community image/data maintainers
- everyone building tools, datasets and documentation around a game complicated enough to justify all of this

And, apparently, thanks to Arknights itself for being inconvenient enough that I eventually built Rhodes Planner.

For detailed attribution, see:

[`CREDITS.md`](CREDITS.md)
