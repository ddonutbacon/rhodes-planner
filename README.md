# Rhodes Planner

**An account-aware Arknights progression, crafting and farming planner.**

> Import your account → choose who you want to build → preserve what you want to keep → craft what you can → farm what is actually missing.

Rhodes Planner grew out of my own love-hate relationship with Arknights and a desire to stop rebuilding the same planning logic by hand.

---

## Try Rhodes Planner

### 🌐 Online

**[Open Rhodes Planner](https://rhodes-planner-ddbacon.streamlit.app/)**

No installation required.

Your normalised Rhodes profile is stored in your browser. Raw ArkPRTS uploads are parsed in memory and are not intentionally persisted by Rhodes Planner.

---

## What it does

- Import an **ArkPRTS full-account JSON export**
- Verify imported LMD against the raw JSON value
- Read owned operators, levels, skills, masteries, modules and materials
- Manually update your account state without repeatedly importing JSON
- Plan multiple operator upgrades together
- Pause/reactivate goals and reorder priorities without deleting them
- Set exact reserve quantities for materials, LMD and EXP
- Use existing materials before recommending farming
- Account for workshop/factory crafting and crafting costs
- Recommend farming stages using **Penguin Statistics**
- Estimate LMD and Battle Record farming
- Account for passive RIIC production
- Copy or download farming targets for Penguin Statistics Planner
- Plan **future operators and materials** before they reach the Global server

---

## How it works

```text
Account / manual starting state
        ↓
Operator goals
        ↓
Active goals only
        ↓
Current inventory
        ↓
Exact reserves
        ↓
Available crafting
        ↓
Shop / acquisition conversions
        ↓
Passive RIIC production
        ↓
What you still need to farm
```

## Privacy

Rhodes Planner does **not** request your Arknights password, email verification codes, authentication tokens or game login session.

On the hosted Streamlit app, the normalised Rhodes profile is stored in browser-local storage rather than a shared server-side profile file. A Rhodes profile can also be exported/imported manually for transfer between browsers or devices.

See [`SECURITY.md`](SECURITY.md) for details.

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

See [`CREDITS.md`](CREDITS.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

## Development

Rhodes Planner is built with **Python and Streamlit**.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app\main.py
```

Run tests with:

```powershell
python -m pytest
```

---

## AI-assisted development

Rhodes Planner was developed through an **AI-assisted iterative development workflow**.

OpenAI's ChatGPT has been the primary implementation, debugging and testing partner. Product direction, feature requirements, UX decisions, validation, privacy/security decisions and release decisions are directed and reviewed by me as the project author.

AI is part of how Rhodes Planner was built.

---

## Licence

Rhodes Planner's original application code is released under the [MIT Licence](LICENSE).

Third-party game data, statistics, images and Arknights intellectual property remain subject to their respective upstream and rights-holder terms.

Rhodes Planner should therefore be treated as a **non-commercial fan and portfolio project**.

---

## Acknowledgements

Thanks to Hypergryph, Yostar, Penguin Statistics, ArknightsAssets, ArkPRTS, ArkPlanner, arkprtserver, community data maintainers, and everyone building tools around a game complicated enough to justify all of this.

And, apparently, thanks to Arknights itself for still going strong after all these years.
