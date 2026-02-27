# Debugging CI Test Failures

## Multi-Version Error Analysis

When tests fail in CI across multiple TYPO3 versions, **always check error messages from ALL matrix combinations** (v13 AND v14, all PHP versions). Different TYPO3 versions often fail with completely different errors for the same root cause.

### Common Error Pairs

| v13 Error | v14 Error | Root Cause |
|-----------|-----------|------------|
| `parseFunc without any configuration` | `No valid attribute "applicationType"` | Missing TSFE bootstrap |
| Method signature mismatch | Missing interface method | API change between versions |
| Deprecated function warning | Fatal: undefined method | Removed API |
| Test passes | `RuntimeException` in DI container | Singleton resolution order changed |

## Debugging Checklist

1. **Get error counts per matrix:**

   ```bash
   gh run view <RUN_ID> --log-failed 2>&1 | grep "There were"
   ```

2. **Compare v13 vs v14 errors** — different errors often mean different root causes

3. **Check regression scope:**
   - Only your new tests fail → your test setup is incomplete
   - Existing tests also fail → your change has side effects (e.g., `$GLOBALS` pollution)

4. **Get detailed errors per version:**

   ```bash
   gh run view <RUN_ID> --log-failed 2>&1 | grep "^build.*13.4.*8.5.*Functional.*) " | head -20
   gh run view <RUN_ID> --log-failed 2>&1 | grep "^build.*14.0.*8.5.*Functional.*) " | head -20
   ```

## Common Pitfalls

### `$GLOBALS['TYPO3_REQUEST']` Pollution

Setting `$GLOBALS['TYPO3_REQUEST']` in `setUp()` affects ALL tests in the class:

- **v14:** Requires `applicationType` attribute — missing it causes `RuntimeException` in PageRenderer/DI container resolution (63+ errors)
- **v13:** Enables additional processing paths — existing test assertions may no longer match (7+ failures)

**Fix:** Set the global only in specific test methods that need it, with `try/finally` cleanup:

```php
$GLOBALS['TYPO3_REQUEST'] = $this->request
    ->withAttribute('applicationType', ApplicationType::FRONTEND);

try {
    // test code
} finally {
    unset($GLOBALS['TYPO3_REQUEST']);
}
```

### Functional Tests Cannot Call `parseFunc()` with TypoScript References

`ContentObjectRenderer::parseFunc($html, null, '< lib.parseFunc_RTE')` requires:
- TypoScript configuration loaded (v13: `LogicException`)
- Full request with `applicationType` (v14: `RuntimeException`)
- `$GLOBALS['TYPO3_REQUEST']` for child cObj instances

**Solution:** Use unit tests (mock `parseFunc`) + E2E tests (real frontend). See `functional-testing.md` for details.

### Test Isolation Between Matrix Entries

Each matrix entry (PHP version × TYPO3 version) runs independently. A test passing on `8.2 + v13` but failing on `8.5 + v14` indicates version-specific behavior, not flakiness.
