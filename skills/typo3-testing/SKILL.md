---
name: typo3-testing
description: "Use when setting up TYPO3 extension test infrastructure, writing unit/functional/E2E/architecture tests, configuring PHPUnit, testing time-dependent code, mutation testing, mocking dependencies, or configuring CI/CD for TYPO3 extensions."
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
| **Fuzz** | Security, parsers, malformed input | Manual |
| **Crypto** | Encryption, secrets, key management | Fast |
| **Mutation** | Test quality verification, 70%+ coverage | CI/Release |

## Setup and Running Tests

```bash
# Setup
<skill-dir>/scripts/setup-testing.sh [--with-e2e]   # Initialize testing
<skill-dir>/scripts/validate-setup.sh               # Validate existing setup
<skill-dir>/scripts/generate-test.sh <Type> <Class> # Generate test file

# Run tests
Build/Scripts/runTests.sh -s unit          # Unit tests
Build/Scripts/runTests.sh -s functional    # Functional tests
Build/Scripts/runTests.sh -s architecture  # Architecture tests (phpat)
Build/Scripts/runTests.sh -s e2e           # E2E tests (Playwright)
Build/Scripts/runTests.sh -s lint          # Linting
Build/Scripts/runTests.sh -s phpstan       # Static analysis
Build/Scripts/runTests.sh -s mutation      # Mutation testing
```

After creating or modifying a test, **always verify** it fails before the fix and passes after. Run the full suite to ensure no regressions.

## Scoring Requirements

| Criterion | Requirement |
|-----------|-------------|
| Unit tests | Required, 70%+ coverage |
| Functional tests | Required for DB operations |
| Architecture tests | **phpat required** for full points |
| PHPStan | Level 10 (max) |

## Reference Documentation

- `references/unit-testing.md` -- UnitTestCase, mocking, FakeClock, assertions
- `references/functional-testing.md` -- FunctionalTestCase, CSV fixtures, DB testing
- `references/functional-test-patterns.md` -- PHPUnit 10+ migration, container reset
- `references/integration-testing.md` -- PSR-18 mocking, OAuth flows
- `references/e2e-testing.md` -- Playwright setup, Page Object Model
- `references/ddev-testing.md` -- Local-only multi-version matrix, Playwright
- `references/test-runners.md` -- runTests.sh customization, Docker orchestration
- `references/architecture-testing.md` -- phpat rules, layer constraints
- `references/accessibility-testing.md` -- axe-core, WCAG compliance
- `references/fuzz-testing.md` -- php-fuzzer, malformed input
- `references/crypto-testing.md` -- sodium testing, key management
- `references/mutation-testing.md` -- Infection config, MSI interpretation
- `references/performance-testing.md` -- timing, memory, throughput
- `references/typo3-v14-final-classes.md` -- interface extraction, mock strategies
- `references/javascript-testing.md` -- Jest, frontend testing, jQuery-to-native-JS migration pitfalls
- `references/quality-tools.md` -- PHPStan, PHP-CS-Fixer, Rector
- `references/ci-cd.md` -- GitHub Actions, GitLab CI workflows
- `references/sonarcloud.md` -- quality gate configuration
- `references/enforcement-rules.md` -- E2E CI rules, DDEV prohibition, troubleshooting
- `references/asset-templates-guide.md` -- infrastructure setup, PHPUnit config, quality tools

## External Resources

- [TYPO3 Testing Documentation](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/)
- [Tea Extension](https://github.com/TYPO3BestPractices/tea) (reference implementation)
- [phpat documentation](https://github.com/carlosas/phpat)
- [Infection PHP documentation](https://infection.github.io/)
- [DDEV documentation](https://ddev.readthedocs.io/)

---

> **Contributing:** https://github.com/netresearch/typo3-testing-skill
