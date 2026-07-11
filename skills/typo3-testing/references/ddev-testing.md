# DDEV Testing for TYPO3 Extensions

DDEV setup and local-environment mechanics are owned by the `typo3-ddev` skill, not this one. See its `references/`:

- `.ddev/config.yaml` setup and PHP/database version matrix -- `quickstart.md`, `0003-php-version-management.md`
- Multi-version local testing, database snapshots, `runTests.sh` integration -- `advanced-options.md`
- Why not to run automated tests via `ddev exec` (masks CI-only failures) -- `quickstart.md`
- DDEV troubleshooting -- `troubleshooting.md`

For running Playwright E2E tests against a DDEV-hosted TYPO3 instance, see `e2e-testing.md` in this skill (`runTests.sh` DDEV network integration, why CI uses GitHub Services instead of DDEV).
