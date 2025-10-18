# Testing Context for AI Assistants

This directory contains tests for the TYPO3 extension.

## Test Type

**[Unit|Functional|Acceptance]** tests

## Test Strategy

<!-- Describe what this directory tests and why -->
<!-- Example: "Unit tests for domain models - validates business logic without database" -->
<!-- Example: "Functional tests for repositories - verifies database queries and persistence" -->
<!-- Example: "Acceptance tests for checkout workflow - validates complete user journey from cart to payment" -->

**Scope:**

**Key Scenarios:**

**Not Covered:** <!-- What is intentionally not tested here -->

## Testing Framework

- **TYPO3 Testing Framework** (typo3/testing-framework)
- **PHPUnit** for assertions and test execution
- **[Additional tools for this test type]:**
  - Unit: Prophecy for mocking
  - Functional: CSV fixtures for database data
  - Acceptance: Codeception + Selenium for browser automation

## Test Structure

### Base Class

Tests in this directory extend:
- **Unit**: `TYPO3\TestingFramework\Core\Unit\UnitTestCase`
- **Functional**: `TYPO3\TestingFramework\Core\Functional\FunctionalTestCase`
- **Acceptance**: Codeception Cest classes

### Naming Convention

- **Unit/Functional**: `*Test.php` (e.g., `ProductTest.php`, `ProductRepositoryTest.php`)
- **Acceptance**: `*Cest.php` (e.g., `LoginCest.php`, `CheckoutCest.php`)

## Key Patterns

### setUp() and tearDown()

```php
protected function setUp(): void
{
    parent::setUp();
    // Initialize test dependencies
}

protected function tearDown(): void
{
    // Clean up resources
    parent::tearDown();
}
```

### Assertions

Use specific assertions over generic ones:
- `self::assertTrue()`, `self::assertFalse()` for booleans
- `self::assertSame()` for strict equality
- `self::assertInstanceOf()` for type checks
- `self::assertCount()` for arrays/collections

### Fixtures (Functional Tests Only)

```php
$this->importCSVDataSet(__DIR__ . '/../Fixtures/MyFixture.csv');
```

**Fixture Files:** `Tests/Functional/Fixtures/`

**Strategy:**
- Keep fixtures minimal (only required data)
- One fixture per test scenario
- Document fixture contents in test or below

### Mocking (Unit Tests Only)

```php
use Prophecy\PhpUnit\ProphecyTrait;

$repository = $this->prophesize(UserRepository::class);
$repository->findByEmail('test@example.com')->willReturn($user);
```

## Running Tests

```bash
# All tests in this directory
composer ci:test:php:[unit|functional|acceptance]

# Via runTests.sh
Build/Scripts/runTests.sh -s [unit|functional|acceptance]

# Specific test file
vendor/bin/phpunit Tests/[Unit|Functional]/Path/To/TestFile.php

# Specific test method
vendor/bin/phpunit --filter testMethodName
```

## Fixtures Documentation (Functional Tests)

<!-- Document what each fixture contains -->

### `Fixtures/BasicProducts.csv`
- 3 products in category 1
- 2 products in category 2
- All products visible and published

### `Fixtures/PageTree.csv`
- Root page (uid: 1)
- Products page (uid: 2, pid: 1)
- Services page (uid: 3, pid: 1)

## Test Dependencies

<!-- List any special dependencies or requirements -->

- [ ] Database (functional tests only)
- [ ] Docker (acceptance tests only)
- [ ] Specific TYPO3 extensions: <!-- list if any -->
- [ ] External services: <!-- list if any -->

## Common Issues

<!-- Document common test failures and solutions -->

**Database connection errors:**
- Verify database driver configuration in `FunctionalTests.xml`
- Check Docker database service is running

**Fixture import errors:**
- Verify CSV format (proper escaping, matching table structure)
- Check file paths are correct relative to test class

**Flaky tests:**
- Use proper waits in acceptance tests (`waitForElement`)
- Avoid timing dependencies in unit/functional tests
- Ensure test independence (no shared state)

## Resources

- [Unit Testing Guide](~/.claude/skills/typo3-testing/references/unit-testing.md)
- [Functional Testing Guide](~/.claude/skills/typo3-testing/references/functional-testing.md)
- [Acceptance Testing Guide](~/.claude/skills/typo3-testing/references/acceptance-testing.md)
- [TYPO3 Testing Documentation](https://docs.typo3.org/m/typo3/reference-coreapi/main/en-us/Testing/)
