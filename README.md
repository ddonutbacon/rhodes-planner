# Rhodes Planner

**A local-first, account-aware Arknights progression, crafting and farming planner.**

> Import your account → choose who you want to build → preserve what you want to keep → craft what you can → farm what is actually missing.

Rhodes Planner started from my own love-hate relationship with Arknights 

---

## Try Rhodes Planner

### 🌐 Online

**[Open Rhodes Planner](https://rhodes-planner-ddbacon.streamlit.app/)**

No installation required.

### 💻 Portable Windows

Prefer to keep everything local?

Download the latest portable Windows release, extract it anywhere, and run:

```text
Rhodes Planner.bat
```

No separate Python, pip, Conda or Streamlit installation is required.

---

## What it does

- Import an **ArkPRTS full-account JSON export**
- Read owned operators, levels, skills, masteries, modules and materials
- Plan multiple operator upgrades together
- Calculate combined material requirements
- Respect materials you want to keep in reserve
- Use existing materials before recommending farming
- Account for workshop crafting and crafting costs
- Recommend farming stages using **Penguin Statistics**
- Estimate LMD and EXP farming
- Account for passive base production
- Export farming targets for Penguin Statistics Planner
- Plan **future operators and materials** before they reach global

---

## How it works

```text
Your account
     ↓
Operator goals
     ↓
Total requirements
     ↓
Current inventory
     ↓
Reserved materials
     ↓
Available crafting
     ↓
Actual deficit
     ↓
What you still need to farm
```

Rhodes does not assume every required material needs to be farmed.

It first asks:

**Do you already own it? Can you craft it? Are you deliberately saving it?**

Only then does it calculate what is genuinely missing.

---

## Privacy

Rhodes Planner does **not** request:

- your Arknights password
- email verification codes
- authentication tokens

ArkPRTS exports are supplied by the user and parsed by Rhodes for planning purposes.

The portable edition is designed as a local-first tool.

See [`SECURITY.md`](SECURITY.md) for the current threat model and implementation details.

---

## Data sources

Rhodes Planner relies on public and community-maintained resources including:

- [ArknightsAssets / ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata)
- [Penguin Statistics](https://penguin-stats.io/)
- [ArkPRTS](https://github.com/ashleney/ArkPRTS)
- ArkPlanner
- the wider ArkPRTS / arkprtserver ecosystem
- community-maintained Arknights data and image resources

Rhodes Planner is an **unofficial, non-commercial fan project** and is not affiliated with Hypergryph or Yostar.

See [`CREDITS.md`](CREDITS.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for detailed attribution.

---

## Development

Rhodes Planner is built with **Python and Streamlit**.

For development:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app\main.py
```

Run the tests with:

```powershell
python -m pytest
```

---

## AI-assisted development

Rhodes Planner was developed through an **AI-assisted iterative development workflow**.

OpenAI's ChatGPT has been the primary implementation, debugging and testing partner.

AI has assisted with coding, refactoring, testing, debugging and documentation.

Product direction, feature requirements, UX decisions, validation, privacy/security decisions and release decisions are directed and reviewed by me as the project author.

AI is part of how Rhodes Planner was built.

---

## Licence

Rhodes Planner's original application code is released under the [MIT Licence](LICENSE).

Third-party game data, statistics, images and Arknights intellectual property remain subject to their respective upstream and rights-holder terms.

Rhodes Planner should therefore be treated as a **non-commercial fan and portfolio project**.

---

## Acknowledgements

Thanks to Hypergryph, Yostar, Penguin Statistics, ArknightsAssets, ArkPRTS, ArkPlanner, arkprtserver, community data maintainers, and everyone building tools around a game complicated enough to justify all of this.

And, apparently, thanks to Arknights itself for existing and staying strong after years of release. 
