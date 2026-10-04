# Security and Privacy

Rhodes Planner is designed as a **local-first personal tool**, not as a hardened public multi-user service.

## Default exposure

The bundled launcher binds Streamlit to `127.0.0.1`. The default `.streamlit/config.toml` keeps XSRF and CORS protections enabled, disables telemetry, and limits uploads to 25 MB.

## ArkPRTS imports

Rhodes Planner accepts user-supplied ArkPRTS JSON exports. The raw upload is parsed in memory and is not intentionally written to disk by Rhodes Planner. The normalized local profile keeps only data needed by active planner features, such as operator progression, advancement inventory, LMD/EXP, saved upgrade goals and planner settings. Pull currencies are not retained by v0.7.3.

Rhodes Planner does not request or store game-login credentials, verification codes, authentication tokens or ArkPRTS sessions.

Never post a real ArkPRTS export in a public GitHub issue.

## Local profile

The normalized profile is stored under the operating system's per-user application-data directory using `platformdirs`. It is plaintext and is **not encrypted at rest**. Anyone with access to the user's operating-system account/files may be able to read it.

Use **Nuke / clear local profile** in the sidebar to remove the persisted Rhodes profile.

## Network requests

Runtime requests are limited to application-defined public sources for game data, drop statistics and community-hosted images. User-supplied JSON is not allowed to provide arbitrary URLs for Rhodes to fetch. Remote operator/material images are loaded from community hosts, so normal network metadata such as the user's IP address may be visible to those hosts.

## Defensive implementation

The codebase avoids dynamic execution/deserialization of uploaded content. Regression tests scan source code for dangerous patterns including `eval`, `exec`, pickle loading, unsafe YAML loading, `os.system`, and `shell=True`.

GitHub security automation is provided for dependency auditing and static analysis. A green workflow is still not equivalent to a professional penetration test.

## Public hosting

Do not assume this build is safe for public multi-user hosting. A hosted service would need, at minimum, authentication, HTTPS, session isolation/expiry, rate limiting, server-side retention rules, stronger logging review, secure secret management, and additional abuse/complexity controls.

## Reporting a security issue

Please report security issues privately to the maintainer rather than attaching real account exports, diagnostics, credentials or tokens to a public issue.
