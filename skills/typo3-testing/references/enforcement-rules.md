# Enforcement Rules

This skill enforces the following patterns. Violations should be flagged and corrected.

## E2E Testing in CI (MANDATORY)

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
