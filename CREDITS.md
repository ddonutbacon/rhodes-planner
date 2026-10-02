# Rhodes Planner — Credits & Sources

Rhodes Planner is an unofficial fan-made Arknights personal toolkit. It is not
affiliated with or endorsed by Hypergryph, Yostar, Penguin Statistics, ArkPRTS,
or the community projects listed below.

## Arknights game content

Arknights and related game data/art remain the property of their respective
rights holders, including Hypergryph and Yostar. Rhodes Planner does not bundle
a static game-data snapshot in its source release.

## Runtime game data

**ArknightsAssets / ArknightsGamedata**  
https://github.com/ArknightsAssets/ArknightsGamedata

Rhodes Planner retrieves selected structured data for operator metadata,
progression costs, items, modules, stages, and workshop formulas. Rhodes Planner
does not assume a dataset license that the upstream repository does not
explicitly publish.

## Farming statistics and planner interoperability

**Penguin Statistics**  
https://developer.penguin-stats.io/public-api

Community drop statistics are used for stage/material farming recommendations.
Penguin's public API documentation asks API users to comply with **CC BY-NC
4.0**. Rhodes Planner is therefore presented as a non-commercial fan/portfolio
project; the MIT license on Rhodes Planner source code does not relicense
Penguin's data.

**Penguin Statistics / ArkPlanner**  
https://github.com/penguin-statistics/ArkPlanner

ArkPlanner is used as a reference for planner interoperability and farming
concepts. The ArkPlanner repository publishes an MIT license.

## Account export ecosystem

**ArkPRTS**  
https://github.com/ashleney/ArkPRTS

**arkprtserver**  
https://github.com/ashleney/arkprtserver

Both projects publish GPL-3.0 licenses. Rhodes Planner does not bundle or call
those projects directly. Users may independently generate an account export and
supply the JSON to Rhodes Planner.

## Community images

**PuppiizSunniiz / Arknight-Images**  
https://github.com/PuppiizSunniiz/Arknight-Images

**Aceship / Arknight-Images**  
https://github.com/Aceship/Arknight-Images

Rhodes Planner requests operator/material images from community-hosted
repositories at runtime. Rhodes Planner does not claim ownership of those game
assets and does not assume a license where an upstream repository does not
clearly publish one.

## Application libraries

Rhodes Planner uses open-source Python libraries including:

- Streamlit — https://streamlit.io/
- Pydantic — https://docs.pydantic.dev/
- pandas — https://pandas.pydata.org/
- Requests — https://requests.readthedocs.io/
- platformdirs — https://github.com/tox-dev/platformdirs

Their respective licenses and copyright notices remain with their maintainers.

## Community thanks

Thank you to the players and maintainers who collect drop samples, maintain
public game-data dumps, document account schemas, and keep Arknights tooling
available to the community.

See also [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the data/license boundary.
