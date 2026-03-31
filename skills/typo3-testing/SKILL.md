---
name: typo3-testing
description: "Use when setting up TYPO3 extension test infrastructure, writing unit/functional/E2E tests, configuring PHPUnit, mutation testing, mocking, CI/CD test pipelines, or debugging CI failures. For existing test suites, run the automated-assessment skill first to identify gaps. Also triggers on: ensure proper testing, test matrix, integration testing, e2e testing, coverage, test generation."
---

# TYPO3 Testing Skill

## Assessment-First Rule

**When enhancing an existing test suite** (not setting up from scratch), run the automated-assessment skill FIRST:

```bash
automated-assessment typo3-testing
```

> Install additional skills (e.g. `typo3-conformance`, `enterprise-readiness`) for broader assessment coverage.

This generates a gap report from 73+ checkpoints covering PHPUnit config, PHPStan level, runTests.sh, CaptainHook hooks, architecture tests, mutation thresholds, CI matrix, and coverage per class.

**Use the assessment report as the task list.** Resolve mechanical checkpoint failures before manual test writing.

### When This Rule Applies
- "enhance/improve/strengthen tests", "increase coverage/mutation score"
- "enterprise grade", "A+ testing", "fix all findings"

### When This Rule Does NOT Apply
- Setting up from scratch, writing a specific test, debugging a failing test

---

References for TYPO3 extension testing.

## Test Type Selection

| Type | Use When | Speed |
|------|----------|-------|
| **Unit** | Pure logic, no DB, validators, utilities | Fast |
| **Functional** | DB interactions, repositories, controllers | Medium |
| **Architecture** | Layer constraints, dependency rules (phpat) | Fast |
| **E2E (Playwright)** | User workflows, browser, accessibility | Slow |
| **Integration** | HTTP client, API mocking, OAuth flows | Medium |
| **Mutation** | Test quality verification, 70%+ coverage | CI/Release |

## runTests.sh - Mandatory

`Build/Scripts/runTests.sh` is mandatory. Must be executable, support `-s` (suite) and `-p` (PHP version).

## Git Hooks

Verify: `ls captainhook.json .git/hooks/pre-commit 2>/dev/null` (see `references/captainhook-setup.md`)

## Running Tests

```bash
Build/Scripts/runTests.sh -s unit          # Unit tests
Build/Scripts/runTests.sh -s functional    # Functional tests
Build/Scripts/runTests.sh -s phpstan       # Static analysis
Build/Scripts/runTests.sh -s cgl           # Coding guidelines
Build/Scripts/runTests.sh -s mutation      # Mutation testing
```

Setup scripts: `scripts/setup-testing.sh`, `scripts/validate-setup.sh`, `scripts/generate-test.sh`.

## Scoring Requirements

| Criterion | Requirement |
|-----------|-------------|
| Unit tests | Required, 70%+ coverage |
| Functional tests | Required for DB operations |
| Architecture tests | **phpat required** for full points |
| PHPStan | Level 10 (max) |

## References (in `references/`)

`unit-testing.md` | `functional-testing.md` | `functional-test-patterns.md` | `integration-testing.md` | `e2e-testing.md` | `ddev-testing.md` | `test-runners.md` | `architecture-testing.md` | `ci-debugging.md` | `ci-cd.md` | `quality-tools.md` | `mutation-testing.md` | `typo3-v14-final-classes.md` | `mock-validity.md` | `javascript-testing.md` | `captainhook-setup.md` | `enforcement-rules.md`

### Content Triggers

- CI test failures across TYPO3 versions: load `ci-debugging.md`
- Functional tests with TSFE context: load `functional-testing.md`
- Mock failures across dependency versions: load `mock-validity.md`

## External Resources

- [TYPO3 Testing Documentation](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/)
- [Tea Extension](https://github.com/TYPO3BestPractices/tea) (reference implementation)
- [phpat documentation](https://github.com/carlosas/phpat)
- [Infection PHP documentation](https://infection.github.io/)
- [DDEV documentation](https://ddev.readthedocs.io/)

---

> **Contributing:** https://github.com/netresearch/typo3-testing-skill
