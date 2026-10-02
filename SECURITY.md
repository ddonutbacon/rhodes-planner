# Rhodes Planner Security & Privacy

## Current model

Rhodes Planner is designed as a local-first application. The Windows launchers
bind Streamlit to `127.0.0.1`, so another device on the LAN cannot connect
unless the user deliberately changes the server configuration.

## ArkPRTS data

ArkPRTS full exports can contain more account information than Rhodes Planner
needs. The importer:

- parses the uploaded JSON in the running process;
- does not write the raw export to disk;
- does not retain UID, nickname, friends/social data or authentication data in
  the normalised planner model;
- persists only normalised roster/depot/planning state locally so the personal toolkit survives restarts;
- writes only public game/drop data to the disk cache;
- never asks for game-account passwords or email verification codes.

The plan/export buttons create a file only when the user explicitly requests it.

## External requests

Rhodes Planner uses hard-coded HTTPS endpoints for public game data, Penguin
Statistics data and community image assets. The ArkPRTS export itself is not
sent to those services.

Remote images are loaded by the user's browser from public GitHub raw-content
hosts, so those hosts receive normal browser/IP metadata.

## Controls currently enabled

- local-only `127.0.0.1` binding in local launchers;
- XSRF protection enabled;
- CORS protection enabled;
- Streamlit usage telemetry disabled;
- 25 MB upload cap;
- JSON-only account parsing;
- no `eval`, `exec`, pickle deserialisation or uploaded-data-driven shell calls;
- fixed external data URLs;
- HTML escaping for account/operator text inserted into custom HTML.

## Remaining risks before public hosting

A public deployment should add authentication, HTTPS termination, explicit
session expiry, a documented data-retention/deletion policy, secrets management,
rate limits, structured logging review, JSON complexity limits, dependency
locking/scanning, and release signing/checksums.

For maximum privacy, a hosted version should also proxy/cache approved image
assets rather than loading them directly in the browser.

## Bug reports

Do not attach a full real ArkPRTS export to a public GitHub issue. Redact
identifiers and provide only the smallest JSON fragment needed to reproduce the
problem.


## Local profile persistence

Rhodes Planner stores the normalized local toolkit profile in the user's
application-data directory. The raw ArkPRTSs JSON is not persisted.

The local profile is **not encrypted at rest**. Anyone who already has access
to the user's Windows account/files can read the normalised roster, depot and
planning state. The sidebar provides a dedicated **Nuke / clear local profile**
control that deletes this file.

Rhodes Planner also discards Orundum and Originite Prime from the normalised local profile because those currencies are outside the current progression/farming scope.


## Automated repository checks

The GitHub Actions security workflow runs:

- `pip-audit` against `requirements.txt`;
- `bandit` against the `rhodes/` and `app/` Python source trees;
- the normal pytest suite runs separately on pushes and pull requests;
- Dependabot checks Python and GitHub Actions dependencies weekly.

These checks reduce supply-chain/static-code risk but do not replace manual
review or make a future public-hosted deployment automatically safe.
