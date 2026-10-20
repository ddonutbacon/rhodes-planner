# Security and Privacy

Rhodes Planner is an unofficial, non-commercial Arknights planning tool delivered primarily as a hosted Streamlit application.

## Hosted profile storage

Rhodes Planner v0.8 stores the **normalised Rhodes profile in the user's browser local storage** by default.

The hosted application does not intentionally save a shared server-side profile containing a user's operators, inventory, goals or reserves.

Users may export/import a normalised Rhodes profile manually to move planning state between browsers or devices.

## ArkPRTS imports

Rhodes Planner accepts user-supplied ArkPRTS JSON exports.

The raw upload is parsed in memory. Rhodes Planner keeps only the normalised data needed by planner features, such as operator progression, advancement inventory, LMD/EXP, saved goals and planner settings.

Rhodes Planner does not request or store game-login credentials, verification codes, authentication tokens or ArkPRTS sessions.

Never post a real ArkPRTS export in a public GitHub issue.

## Session isolation

Streamlit provides separate session state for active browser sessions. Rhodes additionally avoids using a shared server-side profile file in the default hosted configuration.

For local development only, `RHODES_PROFILE_BACKEND=file` enables the legacy local-file profile backend.

## Network requests

Application-defined requests are limited to public community sources for game data and drop statistics. User-supplied JSON is not allowed to provide arbitrary fetch URLs.

Remote operator/material images are loaded from community hosts, so normal network metadata such as an IP address may be visible to those hosts.

## Upload limits and parsing

The application limits supported account/profile JSON uploads to 25 MB and parses JSON without dynamic execution.

Regression tests should continue to guard against dangerous patterns such as `eval`, `exec`, pickle loading, unsafe YAML loading, `os.system`, and `shell=True`.

## Public hosting

The application is intended for public Streamlit hosting, but this does not make it a hardened high-assurance service. Do not add game credentials, authentication tokens or other secrets to Rhodes Planner.

## Reporting a security issue

Please report security issues privately to the maintainer rather than attaching real account exports, diagnostics, credentials or tokens to a public issue.
