---
name: typo3-testing
description: "Agent Skill: TYPO3 extension testing (unit, functional, E2E, architecture, mutation). Use when setting up test infrastructure, writing tests, configuring PHPUnit, or CI/CD. By Netresearch."
---

# TYPO3 Testing Skill

Templates, scripts, and references for comprehensive TYPO3 extension testing.

## Test Type Selection

| Type | Use When | Speed |
|------|----------|-------|
| **Unit** | Pure logic, no DB, validators, utilities | Fast (ms) |
| **Functional** | DB interactions, repositories, controllers | Medium (s) |
| **Architecture** | Layer constraints, dependency rules (phpat) | Fast (ms) |
| **E2E (Playwright)** | User workflows, browser, accessibility | Slow (s-min) |
| **Integration** | HTTP client, API mocking, OAuth flows | Medium (ms) |
| **Fuzz** | Security, parsers, malformed input | Manual |
| **Crypto** | Encryption, secrets, key management | Fast (ms) |
| **Mutation** | Test quality verification, 70%+ coverage | CI/Release |

## Commands

```bash
# Setup infrastructure
scripts/setup-testing.sh [--with-e2e]

# Run tests via runTests.sh
Build/Scripts/runTests.sh -s unit
Build/Scripts/runTests.sh -s functional
Build/Scripts/runTests.sh -s architecture
Build/Scripts/runTests.sh -s e2e

# Quality tools
Build/Scripts/runTests.sh -s lint
Build/Scripts/runTests.sh -s phpstan
Build/Scripts/runTests.sh -s mutation
```

## Scoring

| Criterion | Requirement |
|-----------|-------------|
| Unit tests | Required, 70%+ coverage |
| Functional tests | Required for DB operations |
| Architecture tests | **phpat required** for full points |
| PHPStan | Level 10 (max) |

> **Note:** Full conformance requires phpat architecture tests enforcing layer boundaries.

## References

### Core Testing
- `references/unit-testing.md` - UnitTestCase, mocking, assertions
- `references/functional-testing.md` - FunctionalTestCase, fixtures, database
- `references/functional-test-patterns.md` - Container reset, PHPUnit 10+ migration
- `references/integration-testing.md` - HTTP client testing, API mocking
- `references/e2e-testing.md` - Playwright, Page Object Model, PHP E2E
- `references/ddev-testing.md` - DDEV environment, multi-version testing

### Specialized Testing
- `references/architecture-testing.md` - phpat rules, layer constraints
- `references/accessibility-testing.md` - axe-core, WCAG compliance
- `references/fuzz-testing.md` - nikic/php-fuzzer, security
- `references/crypto-testing.md` - Encryption, secrets, sodium
- `references/mutation-testing.md` - Infection, test quality
- `references/performance-testing.md` - Benchmarks, memory leak detection

### TYPO3 Specific
- `references/typo3-v14-final-classes.md` - Testing final/readonly classes, interface extraction

### Quality & CI
- `references/quality-tools.md` - PHPStan, PHP-CS-Fixer, Rector
- `references/ci-cd.md` - GitHub Actions, GitLab CI

## Templates

### Infrastructure
- `templates/Build/Scripts/runTests.sh` - **Docker-based test orchestration (required)**
- `templates/bootstrap.php` - General test bootstrap
- `templates/UnitTestsBootstrap.php` - Unit test bootstrap with TYPO3 stubs
- `templates/FunctionalTestsBootstrap.php` - Functional test bootstrap

### PHPUnit Configuration
- `templates/UnitTests.xml` - PHPUnit unit test configuration
- `templates/FunctionalTests.xml` - PHPUnit functional test configuration

### Code Quality
- `templates/phpstan.neon` - PHPStan configuration (level 10)
- `templates/phpstan-baseline.neon` - PHPStan baseline for migrations
- `templates/phpat.php` - Architecture test rules
- `templates/phpat.neon` - PHPat PHPStan integration
- `templates/.php-cs-fixer.dist.php` - Code style configuration
- `templates/rector.php` - Rector automated refactoring

### Mutation & Coverage
- `templates/infection.json5` - Infection mutation testing configuration
- `templates/codecov.yml` - Codecov coverage reporting configuration

### CI/CD Workflows
- `templates/github-actions-tests.yml` - Main CI workflow (lint, phpstan, unit, functional)
- `templates/github-actions-e2e.yml` - E2E workflow with DDEV and Playwright

### E2E Testing
- `templates/Build/playwright/` - Playwright setup and configuration
- `templates/Makefile` - Development command shortcuts

### Fixtures
- `templates/fixtures/` - CSV fixture examples (be_users, pages, tt_content)

## External Resources

- [TYPO3 Testing Docs](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/)
- [Tea Extension](https://github.com/TYPO3BestPractices/tea) - Reference implementation
- [phpat](https://github.com/carlosas/phpat) - PHP Architecture Tester
- [Infection PHP](https://infection.github.io/) - Mutation testing
- [DDEV](https://ddev.readthedocs.io/) - Local development environment

---

> **Contributing:** https://github.com/netresearch/typo3-testing-skill
