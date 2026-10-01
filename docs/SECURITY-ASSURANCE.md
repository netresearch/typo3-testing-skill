<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- SPDX-FileCopyrightText: Netresearch DTT GmbH -->

# Security Assurance Case

This document states what users of the typo3-testing skill can and cannot expect in terms of security, and argues why the expectations hold. Every claim names the file that implements it. Vulnerabilities are reported privately as described in the [organisation security policy](https://github.com/netresearch/.github/blob/main/SECURITY.md).

## What the project ships

| Part | Files | Runs code? |
|------|-------|------------|
| Skill instructions and references | `skills/typo3-testing/SKILL.md`, `skills/typo3-testing/references/*.md`, `agents/test-generator.md`, `agents/coverage-analyzer.md` | No. Text an AI agent loads. The text tells the agent which commands to run in the user's extension (see [Actors and trust boundaries](#actors-and-trust-boundaries)). |
| Helper scripts | `skills/typo3-testing/scripts/setup-testing.sh`, `generate-test.sh`, `validate-setup.sh` | Yes. Bash, run by the user or the agent in the root of a TYPO3 extension. |
| Checkpoints | `skills/typo3-testing/checkpoints.yaml` | Indirectly. Data for the assessment runner of `netresearch/automated-assessment-skill`, which runs the `command`/`script` entries in the assessed extension. |
| Templates | `skills/typo3-testing/assets/` | Not in this repository. PHPUnit, PHPStan, Rector, Infection, Playwright, Docker and CI configuration, example tests and `Build/Scripts/runTests.sh`, which the user or `setup-testing.sh` copies into an extension. |
| Repository tooling | `Build/Scripts/validate-skill.sh`, `Build/Scripts/check-plugin-version.sh`, `Build/hooks/`, `scripts/verify-harness.sh`, `tests/test_scripts.py` | Yes, for maintainers and CI only. |

## Security requirements

1. The helper scripts change only the extension in the current directory: through Composer, and by adding files below it. A symbolic link inside the extension takes the files written through it to where it points (see "Symbolic links" below). They never replace an existing file with a template or a generated test.
2. The checkpoints read the assessed extension and write nothing.
3. The skill and its releases are delivered unmodified from this repository.
4. Changes to `main` are proposed as pull requests, on which the checks listed in [README.md](../README.md#governance-and-policies) run. Branch protection of `main` requires a subset of them and does not bind administrators.

## Actors and trust boundaries

- **User**: chooses the extension, runs the scripts or approves the agent's actions. Trusted.
- **AI agent**: loads `SKILL.md`, the references and the agent definitions and follows them. It acts with the user's permissions and the tools the user's agent platform grants.
- **Extension under test**: the user's own code base. The helper scripts treat its `composer.json` and directory layout as input. `setup-testing.sh` runs `composer require --dev ... --no-update` and `composer update --no-progress` in it and, with `-a`, `vendor/bin/codecept bootstrap`. Composer runs the plugins and scripts that the extension and its dependencies declare, and `codecept` is code from the extension's `vendor/`. The references direct the agent to run PHPUnit, PHPStan, Rector, Infection and `Build/Scripts/runTests.sh` in the extension, which execute its code and its test code.
- **Assessment runner**: runs `checkpoints.yaml` in the assessed extension. Its command allowlist (`skills/automated-assessment/scripts/lib/command-allowlist.sh` in that repository) states that it is not a sandbox; it bounds careless checkpoints, not hostile ones.
- **Maintainers and CI**: change and release this repository.

Boundary 1 lies between the helper scripts and the extension they work on: the class name given to `generate-test.sh` is checked before it becomes a file name or PHP code. The extension's own `composer.json` is trusted as the user's file: the PSR-4 namespace read from it is written into the generated test unchecked. Boundary 2 lies between this repository and the user's machine: releases are built and signed in CI. Running Composer, test tools and `runTests.sh` in the extension does not cross a boundary the user has not already crossed by working on it; the skill adds no isolation to it.

## Argument per requirement

### 1. The helper scripts stay inside the extension and keep existing files

- All three scripts take the extension from `$(pwd)` (`PROJECT_DIR`) and build every path they write below it.
- `setup-testing.sh` accepts only `-a` (`getopts ":a"`; anything else prints the usage and exits 1) and exits 1 when `composer.json` is missing. It creates directories with `mkdir -p` and copies each template only when the target does not exist (`[ ! -f ... ]`); it prints the suggested `composer.json` scripts instead of editing the file.
- `generate-test.sh` accepts one of three test types (`unit`, `functional`, `acceptance`, otherwise exit 1) and a class name that must match `^[A-Za-z_][A-Za-z0-9_]*$`. The class name is the only argument that becomes part of a file name or of PHP code, so a path such as `../Foo` or a name carrying PHP syntax is rejected before either is built. It exits 1 when the test file exists and writes a fixture only when none exists. The namespace comes from `composer.json` through `php -r` with `json_decode`; no project code is loaded.
- `validate-setup.sh` takes no arguments and writes nothing. It tests for files and directories, reads `composer.json` with `grep`, and runs `docker ps` to see whether a daemon answers.
- `tests/test_scripts.py` runs each script against layouts built in a temporary directory with `composer`, `codecept` and `docker` replaced by stubs, and checks the calls made, the files written and that existing files are kept.

### 2. The checkpoints only read

- The `command` and `script` checkpoints in `checkpoints.yaml` use read-only tools (`test`, `grep`, `find`, `jq`, `wc`, `xargs`, `printf`, `basename`, `dirname`, `echo`) and, in TT-120 and TT-121, `php -r` with `token_get_all()` over PHP files under `Classes/`, which tokenises the file without executing it. Their only output redirections go to `/dev/null`.
- The file passes the runner's own `validate-checkpoints.sh` (allowlist and schema) and the checkpoint schema step of the shared Skill Validation job.

### 3. Delivered content is the reviewed content

- Releases are built by `.github/workflows/release.yml`, which calls the `netresearch/skill-repo-skill` release workflow with `id-token: write` and `attestations: write`. That workflow signs `SHA256SUMS.txt` keyless with Cosign and attests the release archives and checksums with `actions/attest-build-provenance`.
- `Build/hooks/pre-push` (enabled by `.envrc` through `core.hooksPath`) runs `Build/Scripts/check-plugin-version.sh`, which refuses a push where a semver tag at `HEAD` disagrees with the version in `.claude-plugin/plugin.json`. The shared Skill Validation job checks that `plugin.json` and `.claude-plugin/plugin.json` agree.
- `.github/workflows/scorecard.yml` runs OpenSSF Scorecard on `main` and weekly.

### 4. Pull requests run automated checks

Every workflow declares `permissions: {}` at the top and grants each job only what its reusable workflow needs. The three workflows that run on `pull_request_target` (`auto-merge-deps.yml`, `labeler.yml`, `pr-quality.yml`) call shared workflows and pass no `secrets: inherit`; `auto-merge-deps.yml` passes only the two merge-app secrets, and `pr-quality.yml` states in its header that no checkout of the pull request head may be added. The checks themselves are listed in [README.md](../README.md#governance-and-policies).

## Common weaknesses

| Weakness | Where it could arise | Countermeasure |
|----------|---------------------|----------------|
| CWE-22 path traversal | Class name passed to `generate-test.sh` | Only PHP identifiers are accepted; the test file path is `Tests/<Unit\|Functional\|Acceptance>/<name><suffix>.php`. |
| CWE-94 code injection | Class name placed into the generated PHP file | Same identifier check; the test type selects one of three fixed templates. |
| CWE-78 OS command injection | Script arguments | No argument is passed to `eval` or built into a command string; `setup-testing.sh` takes no value arguments. |
| CWE-73 overwriting user files | Templates and generated tests | Every template copy and every generated file in the helper scripts is guarded by an existence check. `composer.json` changes only through `composer require`. |
| CWE-1104 unmaintained third-party components | Development and CI tools | Pre-commit hooks are pinned by `rev:` in `.pre-commit-config.yaml` and updated by Renovate (`renovate.json`, `pre-commit` manager enabled); the shared workflows pin actions by commit SHA. |
| CWE-798 secret exposure | Commits | Betterleaks scans pull requests to `main` and pushes to `main` (`security.yml`); `.gitleaks.toml` keeps the default rule set and allowlists the file `references/synthetic-secret-fixtures.md`, which documents fake secrets, and one fake Stripe key. GitHub secret scanning with push protection is enabled for the repository. No script reads or stores credentials. |

## What the skill does not protect against

- **Code run in the extension.** `setup-testing.sh` runs Composer, which executes the plugins and scripts of the extension and its dependencies, and with `-a` runs `vendor/bin/codecept`. Following the skill, the agent runs PHPUnit, PHPStan, Rector, Infection and `runTests.sh`, which execute the extension's code, configuration and test code. Use the skill only on extensions whose code and dependencies you would run yourself.
- **Content of the extension reaching the agent.** The agent reads the extension's code and documentation. Instructions hidden in those files are text like any other; the skill does not filter them.
- **Tool restrictions.** `SKILL.md` declares no `allowed-tools`, and the agent definitions declare only a model. Neither restricts what the agent can do; where a skill declares `allowed-tools`, it only pre-approves tools and does not remove tools the agent already has.
- **Checkpoints as containment.** The assessment runner's allowlist is not a sandbox (see above). The checkpoints in this repository only read, but the runner does not enforce that.
- **Templates.** The files under `assets/` configure tools, containers and CI in the user's extension. `runTests.sh` starts containers from public images referenced by tag, not by digest (for example `ghcr.io/typo3/core-testing-*:latest` and `alpine:3.8`), and mounts the extension directory into them read-write. Review the templates before copying; they are not security controls.
- **Symbolic links.** The scripts follow symbolic links in the extension: a linked `Tests/` or `Build/phpunit/` directory receives the files written through it.
- **Maintainer tooling.** `scripts/verify-harness.sh` queries the GitHub API with the local `gh` login when the repository has no local pull request template. It is run by maintainers and CI only.
