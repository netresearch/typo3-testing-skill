<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- SPDX-FileCopyrightText: Netresearch DTT GmbH -->

# Mutation Testing for TYPO3 Extensions

## Overview

Mutation testing verifies test suite quality by introducing small bugs (mutants) into the code and checking if tests catch them. If a test suite has good coverage but low mutation score, the tests may not be actually testing the important behaviors.

> **Key Distinction**: Mutation testing mutates **code** to verify test quality. For testing that mutates **inputs** to find crashes, see [Fuzz Testing](fuzz-testing.md).

| Aspect | Mutation Testing | Fuzz Testing |
|--------|-----------------|--------------|
| **Mutates** | Source code | Input data |
| **Purpose** | Verify test quality | Find crashes/vulnerabilities |
| **Example** | `if (x != y)` → `if (x == y)` | `<img src="` → `<img src="../../../../etc/passwd` |
| **Finds** | Weak/missing tests | Parsing bugs, security issues |
| **Tool (PHP)** | Infection | nikic/php-fuzzer |

## When to Use Mutation Testing

- After achieving high code coverage (70%+) to verify test quality
- Before releases to ensure critical paths are well-tested
- When refactoring to ensure tests catch regressions
- To identify "weak spots" in test coverage

## The Single-Mutant Check: Prove One Regression Guard By Hand

A full Infection run is the wrong tool when the question is narrow: *does the test I just
wrote actually catch the bug I just fixed?* Answer it directly — revert the production line
to its buggy form, run the affected tests, and require them to **fail**; then restore the
fix and require them to pass. A test that stays green both ways guards nothing, and it looks
identical to a working one in a passing suite.

Do this whenever the bug is one a test could plausibly miss: a silently dropped argument, a
default that quietly substitutes for a rejected value, a mocked collaborator that accepts any
call shape. Mock-based tests are especially prone to it — a mock cannot reproduce the real
library's argument filtering, so asserting *how* it was called is the only thing that binds.

Run it through `runTests.sh` so the check inherits the project's Docker PHP-version isolation —
a pass/fail signal is only worth as much as the environment it came from:

```bash
# 1. Baseline: the guard passes
Build/Scripts/runTests.sh -s unit -- --filter=theGuardingTest

# 2. Keep a byte copy outside the checkout, then reintroduce the bug
#    (exact string replace, not a regex sed)
backup="$(mktemp -d)/Thing.php.orig"
cp Classes/Service/Thing.php "$backup"
python3 - <<'PY'
p = 'Classes/Service/Thing.php'
s = open(p).read()
old, new = "save($path, quality: $quality)", "save($path, $quality)"
assert s.count(old) == 1, f'expected 1 occurrence, found {s.count(old)}'
open(p, 'w').write(s.replace(old, new))
PY
grep -n 'save(\$path' Classes/Service/Thing.php   # confirm the edit applied

# 3. The guard MUST fail now
Build/Scripts/runTests.sh -s unit -- --filter=theGuardingTest

# 4. Restore from the copy and confirm green again
cp "$backup" Classes/Service/Thing.php
cmp "$backup" Classes/Service/Thing.php && Build/Scripts/runTests.sh -s unit -- --filter=theGuardingTest
```

Where the project has no `runTests.sh` — or you are already inside the container — the direct
equivalent is `vendor/bin/phpunit -c Build/phpunit/UnitTests.xml --filter=theGuardingTest`. This is
the single-class case that [`test-runners.md`](test-runners.md) reserves plain `phpunit --filter`
for; do not generalise it to running whole suites outside the entry point.

Restore from the copy, not with `git checkout --`: that puts back the last *committed*
state, so when the fix is still uncommitted it discards the fix, and the next run tests the
buggy code again.

Five traps make this check lie:

- **Revert only the code under test.** `git stash` without a pathspec also stashes the new
  test, so the old tests run against the old code and pass: the red step reports green and
  proves nothing about the new cases. Mutate or restore the single production file, and check
  that the number of failing tests matches the number of new cases you expect to fail; a
  different count means the run measured a different pair of files.
- **Verify the mutation applied.** A `sed` pattern that silently matches nothing leaves the
  file untouched, and the suite then "fails" for some unrelated reason — or passes, and you
  conclude the guard is worthless. Assert the occurrence count when replacing, and `grep`
  the file afterwards. Restore from a byte copy and confirm with `cmp` against that copy.
- **Read the failure, not just the exit code.** In an environment with pre-existing failures
  (a missing `gd`/`imagick` extension makes unrelated tests error), a non-zero exit proves
  nothing on its own. Scope the run with `--filter`, or compare the failing-test set against
  the baseline.
- **A mutation that does not compile is not a caught defect.** The trap above assumes the
  mutated file still parses. When the edit breaks syntax — a dropped semicolon, an unmatched
  brace, a wrong indent in a Python or YAML fixture — the runner exits non-zero at *load*
  time, before any assertion runs. The exit code looks like a kill, and comparing against the
  baseline makes it look like a large one: every test in the file fails, not just the guard.
  Assert the file parses before you run anything, and read the log for a parse diagnostic
  rather than trusting the status alone:

  ```bash
  php -l Classes/Service/Thing.php
  python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' tests/test_thing.py
  node --check src/thing.js
  ```

  In a language that rejects unused imports, deleting a call breaks the build without touching
  syntax — `go build ./...` catches that, and `php -l` deliberately does not: an orphaned
  `use` is valid PHP.
- **If a test other than the intended one goes red, suspect the mutation.** The guard you
  wrote should be the thing that catches the defect you built for it. When a different test
  fails instead — or fails *as well* — the usual cause is that the injected defect is not the
  one you meant: it fires earlier, or on a broader path, so a coarser test reaches it first
  and the intended guard is never exercised. That leaves the guard unproven while the run
  reads like a success. Name which test you expect to fail before running, and if the answer
  differs, fix the mutation rather than accepting the tally.

Re-run this after any refactor of the test itself — consolidating duplicated test setup can
quietly detach the assertion from the behaviour it was guarding.

### Running a batch: two ways the tally lies

Injecting several defects in a loop and counting kills is the natural next step, and the
count is the whole output — so an error in the counting reads as a statement about the tests.

- **PHPUnit names a failing test with its full namespace.** The failure line is
  `1) Vendor\Ext\Tests\Unit\Service\ThingTest::theCase`, so a harness matching on the
  short class name at the start of the line matches nothing and reports every mutation as
  survived. Measured: a batch of six defects reported "0 caught" against a suite that in fact
  caught all six, and the number was two minutes away from being written up as "these tests
  assert nothing". Match on `::`, or on the whole line, and print one captured name per
  mutation while developing the harness.
- **Accept a run on its case count *and* its outcome fields.** `Tests: 1` where the file holds
  four is an aborted run — a collection error, a missing bootstrap, a filter that matched one
  case — and its exit code is indistinguishable from a kill. Parse the `Tests: N` line and
  compare against the file's case count. That is necessary and not sufficient: PHPUnit can
  report the full count with every case skipped and exit 0. Count a mutant killed only on an
  assertion failure — exit 1 with `Failures: N` and no `Errors:` — and treat an error, a
  skipped-only run or any other status as an invalid run rather than a kill.

A tally that comes out at 0 or at 100 % is the moment to verify the harness against a known
answer: mutate one line you are sure a named test covers, and check the harness reports that
test.

### When a mutation survives, ask what level the assertion sits at

A surviving mutation has two readings — the code is untested, or the test looks at the wrong
thing — and they need different fixes. Two shapes from one review round on a credential
derivation:

- The test compared a **fingerprint** built from several fields, and the mutation changed only
  one of them. Dropping the username from the id derivation left every account with the same
  id, while length and transports still differed per account, so the fingerprints differed and
  the test passed. The assertion had to move onto the id alone.
- The test then compared ids for **inequality**, and the mutation still survived: with a shared
  derivation the ids differ only by the length they are cut to, so one is a prefix of the other.
  Inequality holds and the disclosure remains. The assertion had to reject a shared prefix.

Both were found by building a mutation for a property rather than for a line. Before accepting
a test as coverage, name the defect it exists to catch and mutate exactly that.

## Tools

### Infection (Recommended)

PHP mutation testing framework with PHPUnit integration.

**Installation:**
```bash
# The extension supports PHP 8.3 and later
composer require --dev "infection/infection:^0.35"

# The extension still supports PHP 8.2
composer require --dev "infection/infection:^0.32 || ^0.35"
```

0.32.0 is the floor. Before it Infection accepts only `webmozart/assert ^1`, and in a TYPO3
project that can downgrade a runtime dependency: TYPO3 reaches `webmozart/assert` through
`phpdocumentor/reflection-docblock`, which accepts `^1.9.1 || ^2`, so Composer resolves 1.x to
satisfy the older Infection. 0.32.0 and later accept `^1.11 || ^2.0`. From 0.33.0 on Infection
requires PHP 8.3, so `^0.35` alone cannot be installed on PHP 8.2; with the second constraint
Composer resolves 0.32.x on PHP 8.2 and 0.35.x on 8.3 and later. Every option this reference
uses exists in both lines. Through `netresearch/typo3-ci-workflows` the constraint is wider
(`>=0.29 <1.0`), so run `composer show infection/infection` -- the resolved version decides
which options exist (`--only-covered` before 0.31, `--with-uncovered` from 0.31 on).

**Key features:**
- Mutates PHP code with various operators
- Integrates with PHPUnit and Pest
- Generates HTML and JSON reports
- Supports incremental analysis

### Stryker (TypeScript and JavaScript)

Mutation testing for frontend plugins tested with Vitest
(`javascript-testing.md`). Paths are relative to the extension root; run
`npx stryker run Build/stryker.config.mjs` from there. The Vitest config must
resolve its `root` from its own location (see `javascript-testing.md`), or
Stryker reports "No tests were executed".

```js
// Build/stryker.config.mjs
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
    testRunner: 'vitest',
    // pnpm's isolated node_modules hides the runner from Stryker's plugin
    // discovery ("Cannot find TestRunner plugin 'vitest'"); name it here.
    plugins: ['@stryker-mutator/vitest-runner'],
    vitest: { configFile: 'Build/vitest.config.ts' },
    ignorePatterns: ['.Build', 'vendor', 'public', '.stryker-tmp'],
    mutate: [
        'Resources/Private/TypeScript/Plugins/**/*.ts',
        '!Resources/Private/TypeScript/Plugins/**/*.d.ts',
    ],
    reporters: ['html', 'clear-text', 'progress'],
    thresholds: { high: 80, low: 40, break: null },
};
```

- **CI image needs `ps`.** Stryker manages its workers through `ps`;
  `node:*-slim` images ship without `procps`, and the job aborts with
  `spawn ps ENOENT`. Use the full `node` image.
- **Tests that read the source with `readFileSync`** see the instrumented code
  in Stryker's sandbox, so their string assertions fail. Exclude those source
  files from `mutate` and say why next to the exclude.
- **Code no test reaches** yields `NoCoverage` mutants, a per-mutant state
  that depends on coverage, not on whether a file has its own test: a suite can
  cover legacy code indirectly. Read the `NoCoverage` list in the report before
  excluding a file, and exclude only files whose mutants are all `NoCoverage`.
  Alternatively keep `break: null` until the score is stable, then set `break`
  to a value the suite already reaches.

## Preflight: Tests Must Pass Before Mutating

Infection runs the configured PHPUnit suite **once, unmutated**, before applying any mutations. If that initial run reports failures or errors -- even a single one -- Infection aborts and reports nothing. In practice, two recurring causes blow up the preflight:

1. **Flaky fuzz tests.** `random_int(0, $n)` legitimately returns `0`, and `random_bytes(0)` then throws `\ValueError("random_bytes(): Argument #1 ($length) must be greater than 0")` (PHP 8.0+ — was `\Error` before). The fuzz suite passes most of the time and randomly fails inside Infection's preflight. **Fix:** use `random_int(1, $n)` (or `max(1, $n)`) anywhere a randomly-chosen length feeds into `random_bytes()` / `openssl_random_pseudo_bytes()` / similar zero-rejecting APIs.
2. **Functional tests included in the unit suite.** If `phpunit.xml` mixes unit and functional suites, Infection tries to boot a database it cannot reach during local mutation runs.
3. **A test case that asserts nothing.** PHPUnit marks it *risky*, which most project configs tolerate -- but Infection does not run your `phpunit.xml`. It writes its own, under the configured `tmpDir` (`phpunitConfiguration.initial.infection.xml` -- with the `infection.json5` in `assets/` that is `.Build/infection/tmp/`), and that config is strict, so PHPUnit exits 1 and Infection aborts with `Project tests must be in a passing state before running Infection` while the same suite is green in CI. The usual source is a data provider whose expectation is an empty array over which the test loops: `'valid key' => ['ext1', []]` iterates zero times and asserts nothing. **Fix:** compare the whole result (`assertSame($expected, $actual)`) instead of searching it for expected entries -- that closes the real gap, since the "valid" cases were the ones testing nothing.

**Rule of thumb:** before running `infection`, run the exact same command Infection will run (`testFrameworkOptions` from `infection.json5`) and confirm it is green. Fix flakes there, not in Infection's CI logs. Add `--fail-on-risky` to that rehearsal: without it the run passes locally and Infection still aborts, because its generated config is stricter than the project's.

**If your PHPUnit config points at a remote schema, Infection needs the network.** It validates the configuration it generates and keeps the `xsi:noNamespaceSchemaLocation` of the config it started from. With `https://schema.phpunit.de/<version>/phpunit.xsd` there, an offline machine dies in `XmlConfigurationManipulator` with `failed to load external entity` before the first mutant, and a green CI job says nothing about the local failure. The `UnitTests.xml` in `assets/` points at the vendored `../../vendor/phpunit/phpunit/phpunit.xsd` and is unaffected -- pointing the schema at the vendored copy is the fix, not a workaround.

## Mutation job passes in a minute

**An invalid PHPUnit configuration stops Infection before the first mutant.** Infection validates the PHPUnit configuration (`phpunit --validate-configuration`) before it starts. PHPUnit 13.4.0 (2026-10-02, [sebastianbergmann/phpunit#6585](https://github.com/sebastianbergmann/phpunit/issues/6585)) removed `depends` from the `executionOrder` values in its schema, so `executionOrder="depends,defects"` makes Infection exit at once. **Fix:** `executionOrder="defects"`. Dependency resolution is the separate `resolveDependencies` attribute (default `true`), and `defects` is valid in PHPUnit 11.5 too. With `cacheResult="false"` (as in the `assets/` configs) remove `executionOrder` altogether: PHPUnit 13 turns `defects` without the result cache into a test runner warning, see "Moving a suite to PHPUnit 13" in [unit-testing.md](unit-testing.md).

**`continue-on-error` hides it.** With `continue-on-error: true` on the Infection step, as in `netresearch/typo3-ci-workflows` `fuzz.yml`, that failure reports a green job after about one minute. Check the job duration and the Infection summary, not the tick.

**`continue-on-error` does not cover the job timeout.** A mutation job that reaches `timeout-minutes` is cancelled and fails the caller's aggregate check. `fuzz.yml` has the input `mutation-timeout-minutes` (default 30, [netresearch/typo3-ci-workflows#311](https://github.com/netresearch/typo3-ci-workflows/pull/311)). Measured: 25,514 mutants took 1 h 10 min on 4 threads (netresearch/t3x-nr-llm, 2026-10-21).

## Suite Layout: Split Unit/Fuzz From Functional

Keep two PHPUnit configs:

- `phpunit.xml` (or `Build/phpunit/UnitTests.xml`) -- unit + fuzz suites only, no DB, fast.
- `phpunit.functional.xml` (or `Build/phpunit/FunctionalTests.xml`) -- functional tests, requires MySQL/MariaDB.

Point Infection's `testFrameworkOptions` at the unit/fuzz config so the preflight is fast and DB-free:

```json5
"testFrameworkOptions": "-c Build/phpunit/UnitTests.xml"
```

Infection also auto-discovers a `phpunit.xml` (or `phpunit.xml.dist`) in `phpUnit.configDir` (defaults to project root) when `testFrameworkOptions` is not used -- it expects the **standard file names**, so do not rename to `phpunit-unit.xml` or similar without setting `phpUnit.configDir` explicitly:

```json5
"phpUnit": {
    "configDir": "Build/phpunit"
}
```

Either pin the config explicitly (`testFrameworkOptions`) or keep the default name and use `phpUnit.configDir` -- never both implicit. This keeps `composer ci:test:php:unit` and `composer ci:test:mutation` running the same PHPUnit invocation, which is the point of the split.

## Configuration

Create `infection.json5` in project root.

> **TYPO3 convention:** When using `.Build/` for vendor dependencies, use the local schema path
> `".Build/vendor/infection/infection/resources/schema.json"` instead of the remote URL. This
> works offline and reflects the actual installed version.

```json5
{
    "$schema": ".Build/vendor/infection/infection/resources/schema.json",
    "source": {
        "directories": [
            "Classes"
        ],
        "excludes": [
            "Domain/Model"  // Skip simple DTOs
        ]
    },
    "logs": {
        "html": ".Build/logs/infection.html",
        "json": ".Build/logs/infection.json",   // read by the PR diff gate
        "text": ".Build/logs/infection.log",
        "summary": ".Build/logs/infection-summary.log"
    },
    "mutators": {
        "@default": true,
        // Disable noisy mutators if needed
        "TrueValue": false,
        "FalseValue": false
    },
    "minCoveredMsi": 80,    // The gate: MSI over code the tests cover
    "testFramework": "phpunit",
    "testFrameworkOptions": "-c Build/phpunit/UnitTests.xml"
}
```

### Which Threshold Gates: `minCoveredMsi`, Not `minMsi`

Since Infection 0.31 code that no test covers is not mutated at all unless the run passes
`--with-uncovered`: untested files are skipped when mutations are generated, and untested
nodes inside a tested file are dropped as well. With no uncovered mutants left in the
denominator, the reported MSI **is** the Covered Code MSI. Both thresholds then compare
against the same number, the higher one binds, and with the usual pair (`minMsi` below
`minCoveredMsi`) `minMsi` never fails a run that `minCoveredMsi` would pass.

The two keys only come apart with the flag. Measured on one TYPO3 extension with Infection
0.35.5 and an unchanged config: the default run generated 2171 mutants; with
`--with-uncovered` it generated 5002, reported a mutation code coverage of 43 % and an MSI of
34 %. A `minMsi` tuned on the default run means something else entirely once the flag is added,
while `minCoveredMsi` means the same in both. So pick one of two shapes:

- **Default run (recommended):** gate on `minCoveredMsi` and leave `minMsi` out -- it is
  redundant here, and a reader takes a declared threshold for a gate.
- **`--with-uncovered` run:** set `minMsi` as well, as the gate on the share of all code whose
  mutants are killed, and expect it far below `minCoveredMsi`.

**Point `source.directories` at the extension's `Classes` root(s).** Because uncovered code
produces no mutants, listing the whole root costs nothing and the scope follows the tests as
they grow. A hand-picked list of subdirectories falls behind: in the run above it had missed
five directories that had gained tests since the list was written. One limit to know: a
directory excluded from coverage in the PHPUnit config's `<source>` element produces no
mutants either, even when it is listed here -- Infection reads coverage, and that code has
none.

## Mutation Operators

Infection applies these types of mutations:

### Arithmetic Operators
```php
// Original
$result = $a + $b;

// Mutants
$result = $a - $b;  // PlusToMinus
$result = $a * $b;  // PlusToMultiplication
```

### Comparison Operators
```php
// Original
if ($value > 10) { ... }

// Mutants
if ($value >= 10) { ... }  // GreaterThan to GreaterThanOrEqual
if ($value < 10) { ... }   // GreaterThan to LessThan
if (true) { ... }          // Always truthy
```

### Boolean Operators
```php
// Original
if ($a && $b) { ... }

// Mutants
if ($a || $b) { ... }  // LogicalAnd to LogicalOr
if ($a) { ... }        // Remove operand
```

### Return Values
```php
// Original
return $value;

// Mutants
return null;           // Return null
return [];             // Return empty array
return !$value;        // Negate boolean
```

### Method Calls
```php
// Original
$this->save($entity);

// Mutant
// Line removed (method call deleted)
```

## Running Mutation Tests

### Via Composer Scripts

```json
{
    "scripts": {
        "ci:test:mutation": [
            "@ci:test:php:unit",
            ".Build/bin/infection --threads=4"
        ],
        "ci:test:mutation:quick": [
            ".Build/bin/infection --threads=4 --min-covered-msi=80"
        ]
    }
}
```

### Via runTests.sh

```bash
# Add to Build/Scripts/runTests.sh
mutation)
    # Run unit tests first to generate coverage
    COMMAND=(.Build/bin/phpunit -c Build/phpunit/UnitTests.xml --coverage-xml=.Build/logs/coverage-xml --coverage-html=.Build/logs/coverage-html)
    ${CONTAINER_BIN} run ${CONTAINER_COMMON_PARAMS} --name unit-${SUFFIX} ${IMAGE_PHP} "${COMMAND[@]}"

    # Run mutation testing
    COMMAND=(.Build/bin/infection --threads=4 --coverage=.Build/logs/coverage-xml)
    ${CONTAINER_BIN} run ${CONTAINER_COMMON_PARAMS} --name mutation-${SUFFIX} ${IMAGE_PHP} "${COMMAND[@]}"
    SUITE_EXIT_CODE=$?
    ;;
```

### Directly

```bash
# Default run: mutates only code the tests cover (Infection 0.31+)
.Build/bin/infection --threads=4

# Also mutate uncovered code (needed for a meaningful minMsi)
.Build/bin/infection --threads=4 --with-uncovered

# With existing coverage
.Build/bin/infection --threads=4 --coverage=.Build/logs/coverage-xml

# Filter to specific directory
.Build/bin/infection --threads=4 --filter=Classes/Service
```

### A scoped run for killing escaped mutants one by one

To work through the escaped mutants of one directory, make the run fast and make it report
instead of gate: mutate only that directory, set both thresholds to 0 and write the JSON log
somewhere of its own. `--filter` matches path substrings, so keep the trailing slash, or
`Classes/SecurityLegacy` is mutated too. `--logger-json` exists from Infection 0.35.11; on
older versions set `logs.json` in the configuration instead.

```bash
.Build/bin/infection --threads=4 --filter=Classes/Security/ \
  --min-msi=0 --min-covered-msi=0 \
  --logger-json=.Build/infection-scoped/infection.json
```

`--filter` limits which files are mutated; the initial test run still collects coverage for
every directory in `source.directories`. When that initial run is the slow part, use a copy of
the configuration with `source.directories` reduced to the one directory, pass it with
`--configuration=<copy>` (Infection otherwise reads the default file), keep it in the
project root so its relative paths still resolve, keep it out of git
(`"$(git rev-parse --git-common-dir)/info/exclude"`) and delete it when you are done: it is a
local instrument, not a second gate.

Then write a test, re-run, and read which mutants are left. Each entry of `escaped` in the
JSON log carries `mutator.mutatorName`, `mutator.originalFilePath`,
`mutator.originalStartLine` and a `diff` (Infection 0.35.12):

```bash
jq -r '.escaped[] | "\(.mutator.originalFilePath):\(.mutator.originalStartLine) \(.mutator.mutatorName)\n\(.diff)"' \
  .Build/infection-scoped/infection.json
```

The MSI of such a run is not the project's score: it covers one directory and no gate. Quote
the score CI reports; use the scoped run to learn which mutant escaped and whether a new test
killed it.

## Interpreting Results

### Mutation Score Indicator (MSI)

Output of a `--with-uncovered` run. Without the flag the uncovered count is 0 and MSI equals
Covered MSI (see [Which Threshold Gates](#which-threshold-gates-mincoveredmsi-not-minmsi)).

```
Mutations:       150 total
Killed:          120 (80%)    ← Tests caught the mutation
Escaped:          15 (10%)    ← Tests MISSED the mutation (bad!)
Errors:            5 (3%)     ← Mutation caused fatal error
Uncovered:        10 (7%)     ← No tests for this code

MSI: 80%                      ← (Killed + Errors) / Total
Covered MSI: 86%              ← MSI for covered code only
```

### Understanding Results

| Status | Meaning | Action |
|--------|---------|--------|
| **Killed** | Test failed when mutant introduced | Good - test is effective |
| **Escaped** | Test passed with mutant | **Bad - add/improve tests** |
| **Errors** | Mutant caused fatal error | Counted as killed — read them before trusting the score (below) |
| **Uncovered** | No test coverage (reported only with `--with-uncovered`) | Add coverage first |
| **Timeout** | Test took too long with mutant | Usually OK |
| **Skipped** | Mutant not tested | Check config |

### Errored Mutants Inflate the Score

Infection counts an errored mutant as killed, so errors raise the MSI. A
few type errors that a mutation provokes are fine. A cluster of errors with
the **same message** is not: it is a defect of the test setup, and the
score built on it is too high. Group the messages before reading the number:

```bash
jq -r '.errored[].processOutput' build/infection-log.json \
  | grep -E 'Message:|Error:' | sort | uniq -c | sort -rn | head
```

The typical cluster is `Class "Vendor\Ext\Tests\...\AbstractFooTest" not
found`. Infection runs PHPUnit once per mutant, filtered to the test files
that cover it. A test base class that only ever loaded because the
directory suite happened to read its file first is then missing, while the
full suite stays green. Reproduce it with one file on its own:

```bash
vendor/bin/phpunit -c <config> path/to/FooSubclassTest.php   # Class "..." not found
```

The fix is an autoload mapping for the test namespaces, and it belongs in
the **root** `composer.json`. In a site project whose extensions come in
through a `path` repository, an extension's own `autoload-dev` is ignored —
Composer reads `autoload-dev` from the root package only:

```json
"autoload-dev": {
  "psr-4": {
    "Vendor\\Ext\\Tests\\": "extensions/ext/Tests/"
  }
}
```

Then check that every test class matches the mapping: for each file under
`Tests/`, `class_exists()` on its declared namespace and class name through
`vendor/autoload.php` must be true. A namespace missing its `Unit\`
segment, or a test declared in the production namespace, stays unloadable.

Declare a shared base class `abstract` and give it the suffix `TestCase`.
A concrete base needs a placeholder test that every subclass inherits, and
PHPUnit 12 warns about an abstract class in a file that matches the suite's
`Test.php` suffix.

After the fix the score drops to its honest value — the former errors now
count as escaped or killed. Derive thresholds such as `minCoveredMsi` from
that run, not from the inflated one.

One same-message cluster is harmless: mutants PHP refuses to compile. The
`Concat` mutator reorders the operands of a concatenation, and on code such
as `(cond ? 'a' : '') . ',' . (cond2 ? 'b' : '')` the printed mutant can be a
nested ternary without parentheses, which PHP 8 rejects at compile time. Infection
reports each as an error ("N errors were encountered") and counts it as
killed. No test could have caught them and nothing is wrong with the setup;
they only explain the error count.

### Equivalent Mutants Escape by Design

An equivalent mutant changes the code without changing any observable
result, so no test can kill it. Recognize the shape before writing tests
for it. A common one in Extbase validators is the `return` directly after
`$this->addError(...)`:

```php
if ($value === '') {
    $this->addError('Value must not be empty.', 1700000001);
    return;   // mutant: this return removed
}
```

Removing the `return` leaves the error recorded, so the value is still
invalid; the checks after it now run as well. The mutant is equivalent only
if those checks can do nothing but add further errors (no exception, no
state change, no call on a collaborator) and no caller depends on the exact
error list. Read the checks after the `return` before classifying the
mutant. Only if stopping at the first error is a contract does a test
asserting the complete error list (count and codes) belong here. Otherwise
leave these escapes in the report instead of chasing the score.

### Target Scores

| Level | MSI | Covered MSI | Use Case |
|-------|-----|-------------|----------|
| Basic | 50%+ | 60%+ | Initial implementation |
| Good | 70%+ | 80%+ | Production code |
| Excellent | 85%+ | 90%+ | Critical/security code |

The MSI column applies to a `--with-uncovered` run only. In a default run MSI equals Covered
MSI, so the Covered MSI column is the one to gate on.

## Improving Mutation Score

### 1. Fix Escaped Mutants

Review the HTML report to find escaped mutants:

```html
<!-- .Build/logs/infection.html -->
<!-- Shows: Original code, Mutated code, Test that should have caught it -->
```

### 2. Add Boundary Tests

```php
// If this escapes:
//   if ($age >= 18) → if ($age > 18)
// Add boundary test:
public function testAgeExactly18IsAllowed(): void
{
    self::assertTrue($this->validator->isAdult(18));
}
```

Time-based checks hide the same gap. An expiry test whose fixtures sit an
hour away from "now" (`exp = now - 3600` and `now + 3600`) passes for both
`$expiresAt < $now` and `$expiresAt <= $now`, so the `<` → `<=` mutant
escapes and nothing pins what happens at the exact second. Decide what the
boundary must do, freeze the clock, and add a fixture **exactly on the
boundary** (`exp == now`) that asserts that decision.

### 3. Add Negative Tests

```php
// If method removal escapes:
//   $logger->error($message);  // removed
// Add test verifying the call:
public function testErrorIsLogged(): void
{
    $logger = $this->createMock(LoggerInterface::class);
    $logger->expects(self::once())
        ->method('error')
        ->with('Expected message');

    $service = new MyService($logger);
    $service->doSomethingThatLogs();
}
```

### 4. Test Return Values

```php
// If return value mutation escapes:
//   return $result; → return null;
// Verify return value explicitly:
public function testReturnsCalculatedValue(): void
{
    $result = $calculator->compute(5, 3);
    self::assertSame(8, $result);  // Not just assertNotNull!
}
```

### 5. Kill Common TYPO3 Escaped Mutants

#### Concat mutations (string reordering/removal)
```php
// WEAK — Concat mutations escape because substring order doesn't matter
$message = $service->getErrorMessage();
self::assertStringContainsString('provider', $message);
self::assertStringContainsString('LLM module', $message);

// STRONG — kills Concat mutations by asserting the exact string
$message = $service->getErrorMessage();
self::assertSame(
    'No LLM provider configured. Create a provider in Admin Tools > LLM > Providers.',
    $message,
);
```

#### LogicalOr to LogicalAnd mutations
```php
// Given this code under test:
//
// public function getStatusMessage(\Throwable $e): string {
//     $msg = $e->getMessage();
//     if (str_contains($msg, '401') || str_contains($msg, 'Unauthorized')) {
//         return 'The API key was rejected.';
//     }
//     return 'An unknown error occurred.';
// }
//
// Test each OR branch individually to kill the LogicalAnd mutation:

#[Test]
public function recognizes401Code(): void
{
    // Only "401", no "Unauthorized" — kills LogicalAnd mutation
    $result = $this->subject->getStatusMessage(
        new \RuntimeException('HTTP 401 error'),
    );
    self::assertSame('The API key was rejected.', $result);
}

#[Test]
public function recognizesUnauthorized(): void
{
    // Only "Unauthorized", no "401"
    $result = $this->subject->getStatusMessage(
        new \RuntimeException('Request Unauthorized'),
    );
    self::assertSame('The API key was rejected.', $result);
}
```

#### GreaterThan to GreaterThanOrEqual mutations
```php
// If code has: $check = $count > 0 ? createOkCheck() : createErrorCheck();
// You must assert BOTH branches to kill the mutation.

// 1. Test for count > 0 (e.g., count = 1)
$passingCheck = $this->service->runCheck(1);
self::assertSame(Severity::Ok, $passingCheck->severity);
self::assertNull($passingCheck->fixRoute);

// 2. Test for count = 0. This kills the `>` to `>=` mutation.
$failingCheck = $this->service->runCheck(0);
self::assertSame(Severity::Error, $failingCheck->severity);
self::assertSame('nrllm_providers', $failingCheck->fixRoute);
```

## CI Integration

### The Rule: The Diff in a Pull Request, the Full Run on a Schedule

A full Infection run over a mature extension takes an hour or more, so it does not belong in
every pull request. Split mutation testing by event:

1. **Pull request / merge request: mutate the diff only.** Run Infection with
   `--git-diff-lines` (changed lines; the default for a change to production code) or a wider
   selection where the change needs it (see [Generation Scope](#generation-scope-which-mutants-a-diff-run-creates)), and
   `--git-diff-base` set to the target branch; Infection resolves the merge base itself (see
   [Incremental Mutation Testing](#incremental-mutation-testing)). The PR pipeline stays short,
   and what it reports are the mutants of the change.
2. **Default branch: the full run on a schedule and on manual dispatch.** Run every mutant
   nightly or weekly, and when started by hand (`workflow_dispatch` on GitHub, a pipeline started
   from the web or the API on GitLab), in a job with a timeout of its own sized to the measured
   run time. The project's MSI thresholds (`minCoveredMsi`, see
   [Which Threshold Gates](#which-threshold-gates-mincoveredmsi-not-minmsi)) gate this run and
   only this run. The MSI of a diff run covers a few mutants of one change and is noise there:
   the diff run passes no MSI threshold. It also mutates the changed lines no test executes
   (`--with-uncovered`) and **fails on any escaped or not covered mutant in the changed
   lines**, and when no test executed any line of the changed files (see the example below).
3. **Codecov receives coverage, not mutation results.** Keep the mutation results in the job log
   or an Infection report artefact, and do not write that the mutation score is tracked in
   Codecov unless the project shows an upload of it there. In t3x-nr-llm below, Codecov gets the
   PHPUnit coverage reports and no step uploads Infection output.

Two projects show the split. In both, a pull request either mutates its diff or runs no mutation
at all; neither runs the full set of mutants per pull request.

- **netresearch/t3x-nr-llm**
  ([`.github/workflows/ci.yml` lines 208-231](https://github.com/netresearch/t3x-nr-llm/blob/7ac10ccfec2af15791da1643001dc525486aaaf8/.github/workflows/ci.yml#L208-L231))
  calls the `fuzz.yml` reusable of `netresearch/typo3-ci-workflows` with `run-mutation-tests`
  true only for `schedule` (weekly) and `workflow_dispatch`, and with
  `mutation-timeout-minutes: 90`. Its pull requests run no mutation job: the reusable's
  Infection call passes no diff option, so a diff run would need a job of its own.
  Coverage goes to Codecov through the `ci.yml` reusable (`upload-coverage: true`). Its MSI
  thresholds do not block yet: the reusable's Infection step is `continue-on-error: true`, and
  the caller calls the job report-only.
- **software-factory/factory** (an internal TYPO3 project) mutates only the lines a merge
  request changes, against the merge request's diff base (`$CI_MERGE_REQUEST_DIFF_BASE_SHA`),
  and runs every mutant on `main` from a nightly pipeline schedule and in pipelines started by
  hand or through the API. It selects the changed lines with a script of its own rather than
  with `--git-diff-lines`, and reports coverage to GitLab rather than to Codecov; the split is
  the same.

### GitHub Actions

```yaml
# .github/workflows/mutation.yml
on:
  pull_request:
  schedule:
    - cron: '0 3 * * 1'  # weekly full run
  workflow_dispatch:

jobs:
  mutation:
    name: Mutation Testing
    runs-on: ubuntu-latest
    # The diff run is short; the full run gets the limit its measured run time needs
    timeout-minutes: ${{ github.event_name == 'pull_request' && 20 || 90 }}
    steps:
      - uses: actions/checkout@v4
        with:
          # Infection computes the merge base; in a shallow clone it falls back to the base ref
          fetch-depth: 0
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.2'
          coverage: xdebug

      - run: composer install

      - name: Mutate the changed lines (pull request)
        if: github.event_name == 'pull_request'
        env:
          BASE_REF: ${{ github.base_ref }}
        run: |
          set -o pipefail
          # logs.json of the infection.json5 under Configuration (with
          # assets/infection.json5 it is .Build/infection/infection.json); removed
          # first so a log of an earlier run cannot answer for this one
          LOG=.Build/logs/infection.json
          rm -f "$LOG"
          .Build/bin/infection \
            --threads=4 \
            --git-diff-lines \
            --with-uncovered \
            --git-diff-base="origin/$BASE_REF" \
            --min-msi=0 \
            --min-covered-msi=0 | tee infection-diff.out
          if [ ! -f "$LOG" ]; then
            # No test executed any line of the changed files: a new class
            # without a test, or a diff of declarations only (see below)
            if grep -q 'No source code from the diff was executed' infection-diff.out; then
              echo "::error::no test executed any line of the changed files"
              exit 1
            fi
            # Infection writes no log when the diff holds no source line to mutate
            grep -qE 'Could not find any modified|No source file found for the filter applied' infection-diff.out \
              || { echo "::error::Infection wrote no log at $LOG"; exit 1; }
            exit 0
          fi
          # -e: a missing field is an error, not a zero
          escaped=$(jq -e '.stats.escapedCount' "$LOG")
          not_covered=$(jq -e '.stats.notCoveredCount' "$LOG")
          echo "generated: $(jq -r '.stats.totalMutantsCount' "$LOG"), escaped: $escaped, not covered: $not_covered"
          if [ "$escaped" != 0 ] || [ "$not_covered" != 0 ]; then
            jq -r '(.escaped[]?, .uncovered[]?) | "\(.mutator.originalFilePath):\(.mutator.originalStartLine) \(.mutator.mutatorName)"' "$LOG"
            echo "::error::$escaped escaped and $not_covered not covered mutant(s) in the changed lines"
            exit 1
          fi

      - name: Full run with the MSI gate (schedule, manual)
        if: github.event_name != 'pull_request'
        run: |
          .Build/bin/infection \
            --threads=4 \
            --min-covered-msi=80

      - name: Upload mutation report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: mutation-report
          path: .Build/logs/infection.html
```

The diff step fails on the escaped and not covered counts, not on a percentage.
`--min-msi=0 --min-covered-msi=0` overrides the thresholds from `infection.json5`, which would
otherwise gate the diff run too: over a handful of mutants one escape moves the score by tens of
points. `stats.escapedCount` and `stats.notCoveredCount` of the JSON log (written by
`logs.json`; both fields exist at this skill's floor 0.32.0; `--logger-json` exists only from
Infection 0.35.11) then decide: any escaped or not covered mutant in the changed lines fails the job and
is listed.

`--with-uncovered` is part of the gate. Without it Infection drops the nodes no test executes
before it creates mutants: a method no test calls, added to a class that has tests, yields 0
mutants and the step passes. With it, those mutants count in `notCoveredCount`.

A run without a log is accepted only when Infection said the diff held nothing to mutate
("Could not find any modified …", "No source file found for the filter applied …"). "No source
code from the diff was executed …" also comes with exit 0 and no log, with or without
`--with-uncovered`, but it means that no test executed any line of the changed files. A new
class without a test produces it, so the step fails. A diff of declarations only (an interface,
abstract method signatures, constants) has no executable line and produces the same message.
Tell the two apart by reading the changed lines: a changed statement inside a function or method
body means a test is missing; for a diff of signatures and declarations alone the gate cannot
judge. The job stays red for such a diff and nothing passes it automatically: a reviewer
confirms that the changed lines hold declarations only and merges past the red job.

### Quality Gate

The MSI gate belongs to the full run on the default branch (schedule and manual dispatch):

```yaml
# Fail the scheduled run if the mutation score drops
- name: Check mutation score
  if: github.event_name != 'pull_request'
  run: |
    .Build/bin/infection \
      --threads=4 \
      --min-covered-msi=80
```

With `--with-uncovered` added, `--min-msi` becomes a second, independent gate; without it the
two options test the same number.

## Best Practices

1. **Run unit tests first** - Mutation testing needs passing tests
2. **Start with low thresholds** - Increase gradually (50% → 60% → 70%)
3. **Focus on covered code** - The default since Infection 0.31 (which removed `--only-covered`); gate on `minCoveredMsi`
4. **Prioritize escaped mutants** - These indicate weak tests
5. **Exclude trivial code** - Skip getters/setters/DTOs in config
6. **Mutate the diff in PRs, everything on a schedule** - `--git-diff-lines` in pull requests, the full run with the MSI gate nightly or weekly (see [CI Integration](#ci-integration))
7. **Document exclusions** - Explain why code is excluded from mutation testing

## Incremental Mutation Testing

The pull-request half of the rule in [CI Integration](#ci-integration). Infection has two diff
modes, and it refuses to combine them:

```bash
# Only the changed lines: the mutants the change itself introduced
# (--with-uncovered: changed lines no test executes count as not covered)
.Build/bin/infection \
  --threads=4 \
  --git-diff-lines \
  --with-uncovered \
  --git-diff-base=origin/main

# Every line of the added and modified files (no --with-uncovered: with the
# not-covered gate, a one-line change to an untested legacy file would fail on
# lines it never touched)
.Build/bin/infection \
  --threads=4 \
  --git-diff-filter=AM \
  --git-diff-base=origin/main
```

### Generation Scope: Which Mutants a Diff Run Creates

State the generation scope of a diff run explicitly. It decides how many mutants the run
creates, not only which survivors you read afterwards.

- **A change to production code only: `--git-diff-lines`.** Infection keeps a mutant when the
  line range of the mutated node overlaps a changed line range of the diff against the merge
  base (`ChangedLinesRange::touches()` in 0.32.7 and 0.35.12). `--git-diff-filter=AM` selects
  changed *files* and mutates every line in them. Measured in an internal project on a direct
  one-line edit of production code: 25 mutants with file selection, 1 with line selection.
- **A one-line edit must not mutate an unrelated expression in the same file.** In

  ```php
  public function discount(Cart $cart): int
  {
      $bonus = $this->config->bonus() * 2;          // unchanged
      if ($cart->subtotal() >= $this->threshold) {  // the edit: > became >=
          return 10 + $bonus;
      }
      return 0;
  }
  ```

  a line-limited run generates the mutants of the `if` line only. A run that also mutates
  `* 2` or the `return` statements was not limited to the change, whatever its survivors say.
- **Wider selection is right where the effect of a change does not sit in changed source
  lines:**
  - *Test-only changes.* A changed or deleted test changes which mutants of unchanged code are
    killed, but no source line changed: `--git-diff-lines` generates nothing and exits 0.
    Mutate the classes the changed tests cover (`--filter=Classes/Service/Thing.php` or their
    directory), or leave them to the scheduled full run and say so in the PR.
  - *Shared fixtures and test configuration.* A changed fixture, base test case,
    `UnitTests.xml` or `infection.json5` affects every test that uses it, and the diff holds no
    source line at all. Run the affected directories or the full set.
  - *Multiline expressions.* Only mutants whose own node touches a changed line are kept. An
    edit to one line of a condition or call wrapped over several lines drops the mutants of the
    other lines of the same expression, although the edit can change whether a test reaches or
    tells them apart. Widen that file (`--filter=<file>`) for such a change.
- **Count the generated mutants, not only the relevant survivors.** A file-wide run with no
  survivor in the changed lines reads like a passing line-limited run. Read
  `stats.totalMutantsCount` from the JSON log (`logs.json`, Infection 0.35.12) and compare it
  with what the changed lines can produce: dozens of mutants for a one-line edit mean the run
  was not limited to its lines.

### Diff Mode in CI

- Both diff options, their mutual exclusion and the merge-base resolution below exist in
  Infection 0.32.7 and 0.35.12 (read in the source); `--git-diff-lines` was added in 0.26.0.
- **Pass the target branch; Infection finds the merge base.** It runs
  `git merge-base <base> HEAD` and diffs against that commit, so what `main` gained after the
  branch point does not count as the PR's change. In a shallow clone that command fails, and
  Infection falls back to the base ref itself with only an info-level log line; it then runs
  `git diff <base>` against the tip of the target branch, so what `main` changed after the
  branch point shows up as a change of the PR. Fetch the full history (`fetch-depth: 0` for
  `actions/checkout`, `GIT_DEPTH: 0` in GitLab CI). In a GitLab merge request pipeline, pass
  `$CI_MERGE_REQUEST_DIFF_BASE_SHA`, the base SHA of the merge request's diff.
- **A PR without changed PHP source passes.** When no file or line of `source.directories`
  changed, Infection prints a success message and exits 0 (0.32.7 and 0.35.12). A
  documentation-only PR needs no guard around the step; a test-only PR needs the wider
  selection above.
- **A PR whose changed source no test executes fails.** Infection prints "No source code from
  the diff was executed by the test framework." as a success and exits 0 (0.32.7 and 0.35.12),
  with or without `--with-uncovered`; the example step above turns it into a failure.
- **The score of a diff run is not the project's score.** Quote the MSI of the scheduled full
  run. The diff run gates on its escaped and not covered counts: any escaped or not covered mutant
  in the changed lines fails it.

## Directory Structure

```
project/
├── infection.json5           # Infection configuration
├── .Build/
│   └── logs/
│       ├── infection.html    # HTML report
│       ├── infection.log     # Detailed log
│       └── infection-summary.log
└── Tests/
    └── Unit/
        └── Service/
            └── MyServiceTest.php
```

## Resources

- [Infection PHP](https://infection.github.io/) - PHP mutation testing framework
- [Mutation Testing](https://en.wikipedia.org/wiki/Mutation_testing) - Concept overview
- [Pitest](https://pitest.org/) - Java mutation testing (for comparison)
- [Stryker](https://stryker-mutator.io/) - JavaScript/TypeScript mutation testing
