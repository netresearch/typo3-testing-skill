---
name: typo3-testing
description: "Use when setting up TYPO3 extension test infrastructure, writing unit/functional/E2E/architecture tests, configuring PHPUnit, testing time-dependent code, mutation testing, mocking dependencies, configuring CI/CD for TYPO3 extensions, or debugging failing tests in CI (including multi-version TYPO3 v13/v14 test failures)."
---

# TYPO3 Testing Skill

Templates, scripts, and references for comprehensive TYPO3 extension testing.

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

**`Build/Scripts/runTests.sh` is mandatory** for all Netresearch TYPO3 extensions. It must be executable and support `-s` (suite) and `-p` (PHP version) flags. CI and local dev must use this script or the same `.Build/bin/` tool paths.

## Setup and Running Tests

```bash
# Setup
<skill-dir>/scripts/setup-testing.sh [--with-e2e]   # Initialize testing
<skill-dir>/scripts/validate-setup.sh               # Validate existing setup
<skill-dir>/scripts/generate-test.sh <Type> <Class> # Generate test file

# Run tests (always via runTests.sh)
Build/Scripts/runTests.sh -s unit          # Unit tests
Build/Scripts/runTests.sh -s functional    # Functional tests
Build/Scripts/runTests.sh -s phpstan       # Static analysis
Build/Scripts/runTests.sh -s cgl           # Coding guidelines
Build/Scripts/runTests.sh -s mutation      # Mutation testing
Build/Scripts/runTests.sh -s ci            # Full CI suite
```

After creating or modifying a test, **always verify** it fails before the fix and passes after.

## Scoring Requirements

| Criterion | Requirement |
|-----------|-------------|
| Unit tests | Required, 70%+ coverage |
| Functional tests | Required for DB operations |
| Architecture tests | **phpat required** for full points |
| PHPStan | Level 10 (max) |

## References

| Reference | Topic |
|-----------|-------|
| `unit-testing.md` | UnitTestCase, mocking, FakeClock |
| `functional-testing.md` | FunctionalTestCase, CSV fixtures, **TSFE limitations** |
| `functional-test-patterns.md` | PHPUnit 10+ migration, container reset |
| `integration-testing.md` | PSR-18 mocking, OAuth flows |
| `e2e-testing.md` | Playwright, Page Object Model |
| `ddev-testing.md` | Local multi-version matrix |
| `test-runners.md` | runTests.sh, Docker orchestration |
| `architecture-testing.md` | phpat, layer constraints |
| `ci-debugging.md` | **Multi-version CI failure analysis** |
| `ci-cd.md` | GitHub Actions, GitLab CI |
| `quality-tools.md` | PHPStan, PHP-CS-Fixer, Rector |
| `mutation-testing.md` | Infection, MSI |
| `typo3-v14-final-classes.md` | Interface extraction, mock strategies |
| `javascript-testing.md` | Jest, frontend testing |
| `enforcement-rules.md` | E2E CI rules, troubleshooting |

All references in `references/` directory.

### Explicit Content Triggers

When debugging CI test failures across TYPO3 versions, load `references/ci-debugging.md` for multi-version error comparison and debugging checklist.

When writing functional tests that need frontend context (parseFunc, typoLink, TSFE), load `references/functional-testing.md` for known limitations and workarounds.

## External Resources

- [TYPO3 Testing Documentation](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/)
- [Tea Extension](https://github.com/TYPO3BestPractices/tea) (reference implementation)
- [phpat documentation](https://github.com/carlosas/phpat)
- [Infection PHP documentation](https://infection.github.io/)
- [DDEV documentation](https://ddev.readthedocs.io/)

---

> **Contributing:** https://github.com/netresearch/typo3-testing-skill
