# Third-Party Notices

Rhodes Planner application code is distributed under the MIT License. Runtime data and game-related assets are separate from the application code and may be governed by different licenses or rights holders.

## Arknights game content

Arknights-related names, characters, artwork and game content belong to their respective rights holders, including Hypergryph and Yostar. Rhodes Planner is an unofficial, non-commercial fan project.

## ArknightsAssets / ArknightsGamedata

Rhodes Planner retrieves selected structured game-data snapshots at runtime for operator progression, items, modules, stages and workshop formulas.

Project: https://github.com/ArknightsAssets/ArknightsGamedata

Rhodes Planner does not bundle a game-data snapshot in its source release and does not assume ownership or a license for the underlying game content.

## Penguin Statistics

Community drop statistics are retrieved from Penguin Statistics for farming recommendations and planner interoperability.

Project/API: https://penguin-stats.io/

Penguin Statistics public-data terms should be followed independently of the MIT license on Rhodes Planner code.

## ArkPRTS / arkprtserver

Rhodes Planner can consume user-supplied account exports produced outside Rhodes Planner. It does not bundle or call ArkPRTS/arkprtserver and does not request game credentials.

ArkPRTS: https://github.com/ashleney/ArkPRTS
arkprtserver: https://github.com/ashleney/arkprtserver

## Recommended external pull calculator

Rhodes Planner v0.7.3 does not embed or copy a pull calculator. [imivi's Arknights Pulls Calculator](https://imivi.github.io/arknights-pulls-calculator/) is credited as a recommended external companion utility. No source code from that project is bundled in Rhodes Planner.

Source: https://github.com/imivi/arknights-pulls-calculator

## Arknights Terra Wiki

Community English terminology for selected CN-only future materials is used only as a display alias when the official EN game-data snapshot does not yet contain the item. Item IDs, quantities, recipes and progression logic still come from ArknightsGamedata.

https://arknights.wiki.gg/

## Community image repositories

Images are requested remotely and are not bundled in Rhodes Planner source releases.

- https://github.com/PuppiizSunniiz/Arknight-Images
- https://github.com/Aceship/Arknight-Images

## Python dependencies

Rhodes Planner uses Python, Streamlit, Pydantic, pandas, Requests and platformdirs. Their own licenses and notices remain with their respective maintainers.
