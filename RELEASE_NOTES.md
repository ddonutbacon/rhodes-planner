# Rhodes Planner v0.7.3

## Portable-path and launcher resilience

- The portable app no longer depends on the root folder being named `portable`.
- The entire Rhodes Planner folder can be renamed or moved to another writable location or drive without changing internal paths.
- The Windows launcher resolves the bundled Python runtime and application from its own location, not from the caller's current working directory.
- Startup now uses a Python launcher that selects port 8501 when available and automatically falls back to the next free local port through 8599.
- Browser launch follows the actual selected local port.
- Missing runtime/application files now produce explicit path diagnostics.
- The portable build filename is generated from `rhodes.__version__`, preventing stale release names.
- Project/package metadata and the HTTP User-Agent now report the same application version.
- HTTP cache writes are atomic. A malformed or partially written cache file is discarded and refreshed instead of preventing startup.
- Cache failures are treated as non-fatal because the cache is an optimization, not user data.

## Previous v0.7.2 fix retained

- Dualchip factory crafting correctly recognizes **2 matching Chip Packs + 1 Chip Catalyst -> 1 Dualchip**.
- Existing reserve and shared-catalyst behavior remains unchanged.
