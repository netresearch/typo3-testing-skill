# Test Runners and Orchestration

The `runTests.sh` script is the **required** TYPO3 pattern for test orchestration, following TYPO3 core conventions.

## Requirements

Extensions **MUST** have a Docker-based `Build/Scripts/runTests.sh` that:

1. Uses **TYPO3 core-testing images** (`ghcr.io/typo3/core-testing-php*`)
2. Supports **multiple databases** (SQLite default, MariaDB, MySQL, PostgreSQL)
3. Supports **multiple PHP versions** (8.2, 8.3, 8.4, 8.5)
4. Works in **CI environments** (auto-detects non-TTY)
5. Handles **database container orchestration** for functional tests

## Template

Use `templates/Build/Scripts/runTests.sh` as starting point. Customize:

1. `NETWORK` variable: Replace `my-extension` with your extension key
2. `COMPOSER_ROOT_VERSION`: Set to your extension version
3. PHPUnit config paths if different from standard

## Basic Usage

```bash
# Show help
./Build/Scripts/runTests.sh -h

# Run unit tests (default)
./Build/Scripts/runTests.sh -s unit

# Run functional tests with SQLite (fastest, no container)
./Build/Scripts/runTests.sh -s functional

# Run functional tests with MariaDB
./Build/Scripts/runTests.sh -s functional -d mariadb

# Run with specific PHP version
./Build/Scripts/runTests.sh -p 8.3 -s unit

# Run quality tools
./Build/Scripts/runTests.sh -s lint
./Build/Scripts/runTests.sh -s phpstan
./Build/Scripts/runTests.sh -s cgl
```

## Script Options

| Option | Description | Values |
|--------|-------------|--------|
| `-s` | Test suite | `unit`, `functional`, `lint`, `phpstan`, `cgl`, `rector` |
| `-d` | Database | `sqlite` (default), `mariadb`, `mysql`, `postgres` |
| `-i` | DB version | mariadb: 10.11, mysql: 8.0, postgres: 16 |
| `-p` | PHP version | `8.2`, `8.3`, `8.4`, `8.5` |
| `-x` | Enable Xdebug | |
| `-n` | Dry-run | For cgl, rector |
| `-u` | Update images | |

## Database Support

### SQLite (Default)
- **Fastest**: No container startup
- **CI-friendly**: No external services needed
- Use for most functional tests

```bash
./Build/Scripts/runTests.sh -s functional  # Uses SQLite
```

### MariaDB/MySQL
- Required for MySQL-specific syntax
- Mark incompatible tests with `#[Group('not-sqlite')]`

```bash
./Build/Scripts/runTests.sh -s functional -d mariadb -i 10.11
./Build/Scripts/runTests.sh -s functional -d mysql -i 8.0
```

### PostgreSQL
- For PostgreSQL compatibility testing

```bash
./Build/Scripts/runTests.sh -s functional -d postgres -i 16
```

## Makefile Integration

Create a `Makefile` for convenient shortcuts:

```makefile
RUNTESTS = Build/Scripts/runTests.sh

.PHONY: test unit functional lint phpstan cs fix ci

test: unit
unit:
	$(RUNTESTS) -s unit

functional:
	$(RUNTESTS) -s functional

func-maria:
	$(RUNTESTS) -s functional -d mariadb

lint:
	$(RUNTESTS) -s lint

phpstan:
	$(RUNTESTS) -s phpstan

cs:
	$(RUNTESTS) -s cgl -n

fix:
	$(RUNTESTS) -s cgl

ci: lint cs phpstan unit
```

## CI/CD Integration

### GitHub Actions (Recommended)

```yaml
name: CI

on: [push, pull_request]

jobs:
  tests:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        php: ['8.2', '8.3', '8.4']
        suite: ['unit', 'functional']
        database: ['sqlite']
        include:
          - php: '8.4'
            suite: 'functional'
            database: 'mariadb'

    steps:
      - uses: actions/checkout@v4

      - name: Run ${{ matrix.suite }} tests
        run: |
          Build/Scripts/runTests.sh \
            -s ${{ matrix.suite }} \
            -p ${{ matrix.php }} \
            -d ${{ matrix.database }}

  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: Build/Scripts/runTests.sh -s lint
      - run: Build/Scripts/runTests.sh -s phpstan
      - run: Build/Scripts/runTests.sh -s cgl -n
```

## PHPUnit Configuration

### Unit Tests (`Tests/Build/phpunit.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="https://schema.phpunit.de/12.5/phpunit.xsd"
    bootstrap="../../.Build/vendor/autoload.php"
>
    <testsuites>
        <testsuite name="Unit">
            <directory>../Unit</directory>
        </testsuite>
    </testsuites>
</phpunit>
```

### Functional Tests (`Tests/Build/FunctionalTests.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="https://schema.phpunit.de/12.5/phpunit.xsd"
    bootstrap="FunctionalTestsBootstrap.php"
>
    <testsuites>
        <testsuite name="Functional">
            <directory>../Functional</directory>
        </testsuite>
    </testsuites>
    <php>
        <env name="TYPO3_CONTEXT" value="Testing"/>
    </php>
</phpunit>
```

## Test Groups

Use PHPUnit groups for database-specific tests:

```php
use PHPUnit\Framework\Attributes\Group;

#[Group('not-sqlite')]  // MySQL-specific syntax
final class MyRepositoryTest extends FunctionalTestCase
{
    // Uses UNSIGNED, AUTO_INCREMENT, etc.
}
```

The `--exclude-group not-${DBMS}` flag automatically excludes incompatible tests.

## Troubleshooting

### TTY Errors
Script auto-detects non-TTY environments. If issues persist:
```bash
CI=true ./Build/Scripts/runTests.sh -s unit
```

### Database Connection Errors
```bash
# Check container is running
docker ps

# Use SQLite to rule out DB issues
./Build/Scripts/runTests.sh -s functional -d sqlite
```

### Update Images
```bash
./Build/Scripts/runTests.sh -u
```

### Permission Issues (Linux)
Script uses `--user $(id -u)` automatically on Linux.

## Best Practices

1. **SQLite First**: Use SQLite for most functional tests (fastest)
2. **Matrix Testing**: Test all supported PHP versions in CI
3. **Group Incompatible Tests**: Use `#[Group('not-sqlite')]` for DB-specific tests
4. **Single Entry Point**: All tests via `runTests.sh`, not direct PHPUnit
5. **Makefile Shortcuts**: Provide `make test`, `make ci` for convenience
6. **Update Images**: Run `-u` periodically to get latest TYPO3 images

## Resources

- [TYPO3 Tea Extension](https://github.com/TYPO3BestPractices/tea) - Reference implementation
- [TYPO3 Core Testing](https://github.com/typo3/typo3) - Core approach
- [typo3/core-testing images](https://github.com/typo3/core-testing) - Official images
