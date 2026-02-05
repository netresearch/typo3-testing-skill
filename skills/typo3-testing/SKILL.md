---
name: typo3-testing
description: "Agent Skill: TYPO3 extension testing (unit, functional, E2E, architecture, mutation). This skill should be used when setting up test infrastructure, writing tests, configuring PHPUnit, testing time-dependent code, mocking dependencies, or configuring CI/CD for TYPO3 extensions. By Netresearch."
---

# TYPO3 Testing Skill

Templates, scripts, and references for comprehensive TYPO3 extension testing.

## Test Type Selection

To select the appropriate test type, use this decision table:

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

### Test Organization Rationale

Organize tests **by feature, not by test type**. This improves discoverability and maintainability:

```
Tests/
├── Unit/
│   └── Domain/Model/UserTest.php        # Tests User model logic
├── Functional/
│   └── Repository/UserRepositoryTest.php # Tests User persistence
└── E2E/
    └── User/Registration.spec.ts         # Tests User registration flow
```

**Why by feature?**
- Finding tests: "Where are User tests?" → Look in User-related directories
- Understanding coverage: All tests for a feature are co-located
- Maintenance: When changing User logic, related tests are easy to find

**Why NOT by test type alone?**
- "All unit tests" doesn't help you understand what's tested
- Scattered tests across unrelated features are hard to maintain

## Setting Up Test Infrastructure

To initialize testing infrastructure for an extension, run:

```bash
scripts/setup-testing.sh [--with-e2e]
```

To validate an existing setup, run:

```bash
scripts/validate-setup.sh
```

To generate a new test file, run:

```bash
scripts/generate-test.sh <TestType> <ClassName>
```

### Test Verification Workflow (MANDATORY)

After creating or modifying a test, you **MUST** verify it works by running the test suite:

1. **Run the new test** to confirm it catches the bug or validates the behavior
2. **Verify failure state** (if TDD): The test should FAIL before the fix is applied
3. **Apply the fix** then re-run to confirm the test now PASSES
4. **Run the full suite** to ensure no regressions

```bash
# Run only the new test first
Build/Scripts/runTests.sh -s unit -- --filter UserValidatorTest

# After fix is applied, run the full suite
Build/Scripts/runTests.sh -s unit
```

**Why this matters:** A test that never fails provides no value. Always verify your test catches the bug before the fix AND passes after.

## Running Tests

To execute tests via the Docker-based runner, use these commands:

```bash
# Unit tests
Build/Scripts/runTests.sh -s unit

# Functional tests
Build/Scripts/runTests.sh -s functional

# Architecture tests (phpat)
Build/Scripts/runTests.sh -s architecture

# E2E tests (Playwright)
Build/Scripts/runTests.sh -s e2e

# Quality tools
Build/Scripts/runTests.sh -s lint
Build/Scripts/runTests.sh -s phpstan
Build/Scripts/runTests.sh -s mutation
```

## Scoring Requirements

To achieve full conformance scores, ensure:

| Criterion | Requirement |
|-----------|-------------|
| Unit tests | Required, 70%+ coverage |
| Functional tests | Required for DB operations |
| Architecture tests | **phpat required** for full points |
| PHPStan | Level 10 (max) |

> **Note:** Full conformance requires phpat architecture tests enforcing layer boundaries.

## Enforcement Rules

This skill enforces the following patterns. Violations should be flagged and corrected:

### E2E Testing in CI (MANDATORY)

| Rule | Enforcement |
|------|-------------|
| **NEVER use DDEV in CI/CD** | Flag any `.github/workflows/*.yml` or `.gitlab-ci.yml` using `ddev` commands |
| **Use GitHub Services** | E2E workflows MUST use MariaDB service container |
| **Use PHP built-in server** | E2E workflows MUST use `php -S` for HTTP, not DDEV |
| **Dual-mode Playwright config** | `playwright.config.ts` MUST use `TYPO3_BASE_URL` env var |

**Why:** DDEV in CI is slow (2-3+ min startup), complex (Docker-in-Docker), resource-heavy, and fragile. The TYPO3 community standard is direct PHP or testing containers.

**Correct pattern:**
```yaml
# GitHub Actions E2E
services:
  db:
    image: mariadb:11.4
    # ...

steps:
  - name: Start PHP server
    run: php -S 0.0.0.0:8080 -t .Build/Web &

  - name: Run Playwright
    env:
      TYPO3_BASE_URL: http://localhost:8080
    run: npm run test:e2e
```

**Incorrect pattern (flag this):**
```yaml
# WRONG - Never do this in CI
- run: ddev start
- run: ddev exec vendor/bin/phpunit
```

## Troubleshooting Test Failures

### E2E Tests Fail

When E2E tests fail, debug systematically:

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| **Timeout on page load** | TYPO3 not started, wrong URL | Check `TYPO3_BASE_URL` env var, verify `php -S` is running |
| **Element not found** | Page not rendered, JS error | Add `await page.waitForLoadState('networkidle')`, check browser console |
| **Login fails** | Missing fixture, wrong credentials | Verify `be_users.csv` fixture loaded, check password hash |
| **Screenshot shows blank page** | PHP error, 500 response | Check `var/log/typo3_*.log`, enable debug mode |
| **Works locally, fails in CI** | See CI debugging section below | Environment differences |

**Debugging steps:**

1. **Capture screenshot on failure** (Playwright does this automatically)
2. **Check Playwright trace** for network requests: `npx playwright show-trace trace.zip`
3. **Verify TYPO3 is accessible**: `curl -I $TYPO3_BASE_URL`
4. **Check TYPO3 logs**: `cat .Build/Web/var/log/typo3_*.log`

### Tests Pass Locally But Fail in CI

This is a common frustration. Use this checklist:

| Check | Local vs CI Difference | Resolution |
|-------|------------------------|------------|
| **PHP version** | Local may differ from CI matrix | Ensure local PHP matches CI target |
| **Database state** | Local has data, CI starts fresh | Add missing fixtures to test setup |
| **File permissions** | Local user differs from CI runner | Avoid hardcoded paths, use `sys_get_temp_dir()` |
| **Timing** | Local is fast, CI is slow | Add explicit waits, avoid `sleep()` |
| **Environment vars** | Local `.env`, CI lacks it | Define all required vars in CI workflow |
| **Extensions loaded** | Local has extra PHP extensions | Check `php -m` output in CI logs |
| **Filesystem case** | macOS case-insensitive, Linux case-sensitive | Fix `require 'MyClass.php'` vs `myclass.php` |

**CI debugging workflow:**

```bash
# 1. Reproduce locally with CI-like conditions
docker run --rm -it php:8.3-cli php -m  # Check extensions

# 2. Add debug output to failing test
$this->markTestSkipped('DEBUG: ' . var_export($actualValue, true));

# 3. Check CI logs for environment differences
# Look for: PHP version, loaded extensions, env vars

# 4. Use GitHub Actions debug logging
env:
  ACTIONS_STEP_DEBUG: true
```

**Golden rule:** If tests pass locally but fail in CI, the bug is in your test's assumptions about the environment, not in the CI.

## Using Reference Documentation

### Core Testing References

When writing unit tests, consult `references/unit-testing.md` for UnitTestCase patterns, mocking strategies, and assertion examples.

When testing time-dependent code (schedulers, cache expiration, TTL), consult `references/unit-testing.md` for FakeClock patterns, Symfony Clock component usage, and Carbon setTestNow() for deterministic time testing.

When writing functional tests, consult `references/functional-testing.md` for FunctionalTestCase setup, CSV fixtures, and database testing patterns.

When migrating to PHPUnit 10+ or fixing container issues, consult `references/functional-test-patterns.md` for container reset patterns and migration guides.

When testing HTTP clients or external APIs, consult `references/integration-testing.md` for PSR-18 mocking, OAuth flow testing, and request capturing.

When writing browser-based E2E tests, consult `references/e2e-testing.md` for Playwright setup, Page Object Model patterns, and PHP-based E2E alternatives.

When setting up DDEV for **local** testing, consult `references/ddev-testing.md` for multi-version matrix testing and Playwright integration. **Note: DDEV is for LOCAL development only - never use DDEV in CI/CD.**

When configuring test runners, consult `references/test-runners.md` for runTests.sh customization and Docker orchestration.

### Specialized Testing References

When enforcing architecture rules, consult `references/architecture-testing.md` for phpat configuration, layer constraints, and dependency rules.

When testing accessibility, consult `references/accessibility-testing.md` for axe-core integration and WCAG compliance testing.

When testing parsers or security-critical code, consult `references/fuzz-testing.md` for nikic/php-fuzzer patterns and malformed input generation.

When testing encryption or secrets, consult `references/crypto-testing.md` for sodium testing patterns and key management verification.

When measuring test quality, consult `references/mutation-testing.md` for Infection configuration and MSI interpretation.

When benchmarking performance, consult `references/performance-testing.md` for timing measurements, memory leak detection, and throughput testing.

### TYPO3 Specific References

When testing against TYPO3 v14 final/readonly classes, consult `references/typo3-v14-final-classes.md` for interface extraction and mock strategies.

When writing JavaScript/TypeScript tests, consult `references/javascript-testing.md` for Jest and frontend testing patterns.

### Quality & CI References

When configuring static analysis, consult `references/quality-tools.md` for PHPStan, PHP-CS-Fixer, and Rector setup.

When setting up CI/CD pipelines, consult `references/ci-cd.md` for GitHub Actions and GitLab CI workflows.

When integrating SonarCloud, consult `references/sonarcloud.md` for quality gate configuration.

## Using Asset Templates

### Infrastructure Setup

To set up Docker-based test orchestration, copy `assets/Build/Scripts/runTests.sh` to your extension. This is the **required** foundation for all test execution.

To initialize test bootstrapping, use these templates:
- `assets/bootstrap.php` - General test bootstrap with autoloader detection
- `assets/UnitTestsBootstrap.php` - Unit test bootstrap with optional TYPO3 stub autoloader
- `assets/FunctionalTestsBootstrap.php` - Functional test bootstrap for TYPO3 testing framework

### PHPUnit Configuration

To configure PHPUnit, copy and customize:
- `assets/UnitTests.xml` - Unit test suite configuration
- `assets/FunctionalTests.xml` - Functional test suite configuration

### Code Quality Tools

To set up static analysis and code style, use:
- `assets/phpstan.neon` - PHPStan level 10 configuration
- `assets/phpstan-baseline.neon` - Baseline template for legacy code migration
- `assets/phpat.php` - Architecture test rules for layer enforcement
- `assets/phpat.neon` - PHPat PHPStan extension configuration
- `assets/.php-cs-fixer.dist.php` - PHP-CS-Fixer code style rules
- `assets/rector.php` - Rector automated refactoring configuration

**CGL Enforcement:** TYPO3 CGL is strict about alignment (e.g., `binary_operator_spaces` in `setUp()` methods). Always run `composer ci:cgl` or the project's CS fixer before committing. Do not rely on manual formatting.

### Mutation Testing & Coverage

To configure mutation testing, copy `assets/infection.json5` and adjust mutator settings and MSI thresholds.

To configure coverage reporting, copy `assets/codecov.yml` for Codecov integration.

### CI/CD Workflows

To set up GitHub Actions, use:
- `assets/github-actions-tests.yml` - Main CI workflow (lint, phpstan, unit, functional tests)
- `assets/github-actions-e2e.yml` - E2E workflow with **GitHub Services + PHP built-in server** (NOT DDEV)

### E2E Testing Setup

To set up Playwright E2E testing, copy the `assets/Build/playwright/` directory containing:
- `package.json` - Node.js dependencies
- `playwright.config.ts` - Playwright configuration
- `tests/playwright/` - Test structure with login setup, fixtures, and example specs

### Development Shortcuts

To add common command shortcuts, copy `assets/Makefile` for make-based task execution.

### Docker Services

To configure additional Docker services for testing, use templates from `assets/docker/`:
- `docker-compose.yml` - Base Docker Compose configuration
- `codeception.yml` - Codeception-specific Docker setup

### Example Tests

To see test patterns in action, review examples in `assets/example-tests/`:
- `ExampleUnitTest.php` - Unit test structure and assertions
- `ExampleFunctionalTest.php` - Functional test with fixtures
- `ExampleAcceptanceCest.php` - Codeception acceptance test

### Database Fixtures

To set up test data, use CSV fixtures from `assets/fixtures/`:
- `be_users.csv` - Backend user fixture with password hashes
- `pages.csv` - Page tree structure
- `tt_content.csv` - Content elements
- `sys_category.csv` - Category hierarchy

Consult `assets/fixtures/README.md` for fixture format documentation.

### AI Agent Documentation

To document AI agent behavior for your extension, use `assets/AGENTS.md` as a template.

## External Resources

When understanding TYPO3 testing patterns, consult the [TYPO3 Testing Documentation](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/).

When seeking reference implementations, study the [Tea Extension](https://github.com/TYPO3BestPractices/tea).

When implementing architecture tests, consult [phpat documentation](https://github.com/carlosas/phpat).

When configuring mutation testing, consult [Infection PHP documentation](https://infection.github.io/).

When setting up DDEV environments, consult [DDEV documentation](https://ddev.readthedocs.io/).

---

> **Contributing:** https://github.com/netresearch/typo3-testing-skill
