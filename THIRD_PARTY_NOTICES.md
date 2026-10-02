# Third-Party Notices and Data Licensing

Rhodes Planner's **original source code** is released under the MIT License.
That license does not grant rights to third-party data, game content, artwork,
trademarks, or external projects used at runtime.

## Penguin Statistics

- Project: https://penguin-stats.io/
- Public API documentation: https://developer.penguin-stats.io/public-api
- Use in Rhodes Planner: community drop statistics and planner interoperability.
- Data terms: Penguin Statistics' public API documentation asks API users to
  comply with **Creative Commons Attribution-NonCommercial 4.0 International
  (CC BY-NC 4.0)**.

**Practical effect:** Rhodes Planner is published as a non-commercial fan and
portfolio project. The MIT license on Rhodes Planner code does not relicense
Penguin Statistics data. Commercial deployment that depends on Penguin data
requires separate review/permission.

## Penguin Statistics / ArkPlanner

- Repository: https://github.com/penguin-statistics/ArkPlanner
- License: MIT
- Use in Rhodes Planner: interoperability/reference only; ArkPlanner source is
  not bundled into Rhodes Planner.

## ArknightsAssets / ArknightsGamedata

- Repository: https://github.com/ArknightsAssets/ArknightsGamedata
- Use in Rhodes Planner: runtime retrieval of selected structured progression,
  item, stage, module and workshop fields.
- License status: Rhodes Planner does **not** assume an explicit dataset license
  where the upstream repository does not clearly publish one.
- Distribution policy: no game-data snapshot is committed or bundled in the
  Rhodes Planner release.

## ArkPRTS and arkprtserver

- https://github.com/ashleney/ArkPRTS — GPL-3.0
- https://github.com/ashleney/arkprtserver — GPL-3.0

Rhodes Planner does not bundle, import, link to, or call these projects. Users
may independently generate a JSON account export and provide that data to Rhodes
Planner. Consuming the user's JSON data does not incorporate GPL source code
into Rhodes Planner.

## Community image repositories

- https://github.com/PuppiizSunniiz/Arknight-Images
- https://github.com/Aceship/Arknight-Images

Rhodes Planner requests selected game images at runtime. The image files are not
bundled in the code release. Rhodes Planner does not claim ownership or assume a
license where an upstream repository does not clearly publish one.

## Arknights intellectual property

Arknights, operator names, game artwork, item artwork and related game content
remain the property of their respective rights holders, including Hypergryph
and Yostar. Rhodes Planner is unofficial and unaffiliated.

## Python dependencies

Rhodes Planner installs its Python dependencies separately through pip. Major
project licenses include:

- Streamlit — Apache-2.0
- Pydantic — MIT
- pandas — BSD-3-Clause
- Requests — Apache-2.0
- platformdirs — MIT
- pytest — MIT (development/test dependency)

Their licenses and notices remain with their respective maintainers.
