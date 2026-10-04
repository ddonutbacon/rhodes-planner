# Rhodes Planner

**Account-aware Arknights progression, crafting and farming planning.**

Rhodes Planner is an unofficial, non-commercial fan project built with Python and Streamlit. It turns an account state into upgrade requirements, crafting routes and farming targets, including future CN-only progression content. It began as the culmination of my love-hate relationship with Arknights and a desire to stop rebuilding the same planning logic by hand.

## v0.7.3 highlights

- **Dualchip factory crafting:** 2 matching Chip Packs + 1 Chip Catalyst now correctly satisfy 1 class Dualchip before Rhodes creates farming deficits.

- **English display names for CN-only operators/materials** where community terminology is available
- **Per-operator requirement breakdowns** plus combined material totals
- **CN-complete planner catalog** for pre-planning operators not yet released on EN
- CN-side promotion, skill, mastery, module, material and workshop dependencies
- future-material awareness with clear **CN only / future EN** status
- dynamic Penguin Statistics farming availability, including new drops added to existing stages
- ArkPRTS full-account JSON import
- persistent local profile
- crafting-aware and reserve-aware farming logic
- T3-first high-tier material expansion
- LMD/EXP/base-production planning
- Penguin Statistics planner-config export
- self-contained portable Windows deployment support
- root-folder-name-independent launcher: the complete app folder can be renamed or moved
- automatic local-port fallback when 8501 is already in use

## Quick start

### Recommended: portable Windows release

1. Download the latest portable release ZIP.
2. Extract the entire folder.
3. The extracted root folder may be renamed or moved as a whole.
4. Double-click **`Rhodes Planner.bat`**.
5. Rhodes Planner starts on `127.0.0.1` and opens in your browser. It prefers port `8501` and automatically chooses another local port if that port is already busy.

No global Python, pip, Conda or Streamlit installation is required when using the portable release.

### Developer installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app\main.py --server.address 127.0.0.1
```

## Account import and privacy

Rhodes Planner can import a user-supplied **ArkPRTS full-account JSON export**. The raw file is parsed in memory and is not intentionally persisted by Rhodes Planner.

The local profile stores normalized planner state only. It is plaintext and is not encrypted at rest. Use **Nuke / clear local profile** in the sidebar to remove it.

Rhodes Planner does not request game-login credentials, verification codes or authentication tokens.

See [SECURITY.md](SECURITY.md) for the threat model and limitations.

## Data sources

Rhodes retrieves public/community data at runtime rather than bundling game-data snapshots.

- [ArknightsAssets / ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata)
- [Penguin Statistics](https://penguin-stats.io/)
- [ArkPRTS](https://github.com/ashleney/ArkPRTS) export ecosystem
- community image repositories documented in [CREDITS.md](CREDITS.md)

## Development approach

Rhodes Planner was developed through an **AI-assisted iterative development workflow**. AI tools assisted with implementation, debugging, refactoring and test generation. Product direction, requirements, UX decisions, validation, privacy/security decisions, testing scenarios and release decisions were directed and reviewed by the project author.

## Tests

```powershell
python -m pytest
```

The regression suite includes progression/crafting behavior, future-content localization/handling, ArkPRTS privacy behavior and security-oriented static checks.

## License and attribution

Rhodes Planner application code is licensed under the [MIT License](LICENSE).

Runtime game data, community drop statistics, images and Arknights intellectual property are not relicensed by the Rhodes Planner MIT license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [CREDITS.md](CREDITS.md).


## Acknowledgements

Rhodes Planner stands on a large amount of community work. Sincere thanks to **Hypergryph and Yostar**, [ArknightsAssets / ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata), [Penguin Statistics](https://penguin-stats.io/), [ArkPlanner](https://github.com/penguin-statistics/ArkPlanner), [ArkPRTS](https://github.com/ashleney/ArkPRTS), [arkprtserver](https://github.com/ashleney/arkprtserver), [imivi's Arknights Pulls Calculator](https://imivi.github.io/arknights-pulls-calculator/), community image maintainers, and the broader Arknights tooling/data community.

Development was AI-assisted, with **OpenAI's ChatGPT** used as the primary implementation/debugging/testing partner. Product direction, requirements, validation, UX, privacy/security choices and release decisions were directed and reviewed by the project author.

For fuller attribution and license boundaries, see [CREDITS.md](CREDITS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
