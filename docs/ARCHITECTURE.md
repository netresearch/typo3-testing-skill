# Architecture

## Purpose

This repository is an AI agent skill that provides procedural knowledge, templates, and scripts for setting up and running tests in TYPO3 extensions. It covers unit, functional, E2E (Playwright), architecture (phpat), integration, and mutation testing.

## Component Overview

### Skill Definition (`skills/typo3-testing/`)

The core skill package following the Agent Skills specification:

- **SKILL.md**: Entry point loaded by AI agents. Contains test type selection logic, workflow steps, and scoring requirements.
- **assets/**: Template files that agents install into target extensions -- PHPUnit configs, PHPStan configs, Rector configs, Makefile, CI workflow templates, Docker configs, and example tests.
- **references/**: 21 detailed reference documents covering each testing domain (unit, functional, E2E, architecture, mutation, CI/CD, etc.).
- **scripts/**: Helper scripts for initializing test infrastructure (`setup-testing.sh`), generating test scaffolds (`generate-test.sh`), and validating setups (`validate-setup.sh`).
- **checkpoints.yaml**: Evaluation checkpoint definitions for skill quality scoring.

### Agents (`agents/`)

Specialized agent definitions:
- **test-generator.md**: Agent focused on creating tests for specific classes or scenarios.
- **coverage-analyzer.md**: Agent focused on analyzing and improving code coverage.

### Evaluations (`evals/`)

Test cases for validating skill quality and correctness.

### Build (`Build/`)

Git hooks (pre-commit, pre-push) and utility scripts for repository maintenance.

## Data Flow

1. Agent loads `SKILL.md` when testing intent is detected
2. For new setups, agent runs `scripts/setup-testing.sh` which copies assets into the target extension
3. Agent references `references/` docs for test-type-specific patterns and best practices
4. Agent generates tests using `scripts/generate-test.sh` or manually based on reference patterns
5. Tests are executed via `Build/Scripts/runTests.sh` in the target extension

## Key Design Decisions

- **runTests.sh as standard**: All TYPO3 extensions must use this pattern for local-CI parity.
- **Asset-based templating**: Config files are copied and adapted, not generated dynamically.
- **Comprehensive reference library**: Each testing domain has its own reference doc to keep instructions focused and maintainable.
- **Separate agents for sub-tasks**: Test generation and coverage analysis are distinct concerns with dedicated agents.
