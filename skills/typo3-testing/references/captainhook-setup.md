<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- SPDX-FileCopyrightText: Netresearch DTT GmbH -->

# CaptainHook Setup for TYPO3 Extensions

CaptainHook is the standard git hook framework for TYPO3/PHP projects.
It auto-installs via a Composer plugin on `composer install`.

## Netresearch Default: `Build/captainhook.json`

Keep testing/CI config under `Build/` so the repo root stays focused on
end-user files (README, LICENSE, composer.json, ext_emconf.php).
`captainhook/hook-installer` reads the config path from composer.json, so
`Build/captainhook.json` is a fully supported, equivalent location.

## How It Works

1. `Build/captainhook.json` defines hooks (pre-commit, commit-msg, pre-push).
2. `composer.json` declares the path via `extra.captainhook.config`:

   ```json
   {
     "config": {
       "allow-plugins": {
         "captainhook/hook-installer": true
       }
     },
     "extra": {
       "captainhook": {
         "config": "Build/captainhook.json",
         "only-enabled": true
       }
     }
   }
   ```

3. `captainhook/hook-installer` auto-installs hooks on every `composer install`,
   reading the Build/ path automatically. `netresearch/typo3-ci-workflows` requires
   it (`^1.0.5`). `captainhook/captainhook` does not (checked for 5.29.3): without the
   meta-package, add `captainhook/hook-installer` to `require-dev`. Do not use
   `captainhook/plugin-composer` 5.3.3: it installs all eight hook types and can abort
   `composer install` in a worktree of a bare repository.
   `only-enabled` installs only the hook types that the config enables. Without it,
   disabled hook types are installed too, and one written by CaptainHook 5.29.2 or
   earlier can make `git worktree add` exit 127. The key does not remove hooks that
   are already installed (see Troubleshooting).
4. Hooks run standard CI commands locally before commit/push.

## Typical Build/captainhook.json for TYPO3

```json
{
  "config": {"bootstrap": "../.Build/vendor/autoload.php"},
  "pre-commit": {
    "enabled": true,
    "actions": [
      {"action": "composer ci:test:php:cgl"},
      {"action": "composer ci:test:php:phpstan"}
    ]
  },
  "commit-msg": {
    "enabled": true,
    "actions": [
      {
        "action": "\\CaptainHook\\App\\Hook\\Message\\Action\\Rules",
        "options": ["\\CaptainHook\\App\\Hook\\Message\\Rule\\MsgNotEmpty"]
      }
    ]
  },
  "pre-push": {
    "enabled": true,
    "actions": [
      {"action": "composer ci:test:php:unit"}
    ]
  }
}
```

Every hook needs `enabled` and `actions`; without `enabled`, 5.29.3 stops with
`invalid hook configuration`. `bootstrap` is relative to the config file: use
`../vendor/autoload.php` where `vendor-dir` is `vendor`.

## Setup

```bash
# CaptainHook installs automatically with Composer
composer install

# Verify hooks are installed
ls -la .git/hooks/pre-commit
```

## Migrating from root `captainhook.json`

```bash
git mv captainhook.json Build/captainhook.json
# then add to composer.json:
#   "extra": {"captainhook": {"config": "Build/captainhook.json", "only-enabled": true}}
# and make "bootstrap" in the config relative to Build/
# plain clone only: overwrites the enabled hooks, a plain install skips existing ones
CAPTAINHOOK_FORCE_INSTALL=true composer install
```

## Troubleshooting

- If hooks don't install in a plain clone:
  `.Build/bin/captainhook install --force --only-enabled --configuration=Build/captainhook.json`
  (`vendor/bin/captainhook` where `bin-dir` is the default)
- Git worktrees: `hook-installer` 1.0.5 or later prints `install is skipped` and exits 0.
  An older version aborts with `invalid .git path`: upgrade it. Creating a hooks
  directory does not help.
- Installed hooks that fail in a fresh worktree: git-workflow skill,
  `references/git-hooks-setup.md`, "Lasting fix for CaptainHook".
- In a container: `typo3-ci-workflows` README, section "Git worktrees".
