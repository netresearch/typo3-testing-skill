<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- SPDX-FileCopyrightText: Netresearch DTT GmbH -->

# Crash and Concurrency Testing

Use this guide when a TYPO3 extension claims atomic writes, crash recovery or
correctness across overlapping requests. Ordinary logic fixes still use the
normal [TDD loop](tdd-discipline.md); they do not require a formal model.

## Choose the Claim and Persistence Boundary

Name the invariant, participating tables, connection and commit owner. For an
audited mutation, include the value, MM relations, audit row and integrity anchor
where the contract requires them to commit together. Assert stored state through
a fresh reader, not only calls on a transaction mock.

Resolve the connections actually used by the services. TYPO3 table mappings can
route writes to different connections; a transaction on one does not protect the
others. Test rejection of unsupported split mappings or enclosing transactions
if the implementation requires sole ownership. Releasing a savepoint is not an
outer commit, and locks must cover the final commit that makes writes visible.
Also test the supported successful path; rejecting every request is not atomicity.

Use the database engine and isolation level relevant to the claim. SQLite is
useful for a local persistence probe, but its passing result does not establish
MySQL/PostgreSQL locking behavior. Document the actual backend and configuration.
Listener database writes participate only if they use the same transaction.
Check external cache invalidations, emitted events and remote audit sinks
separately; a database rollback does not reverse those effects.

## Distinguish an Exception from Process Loss

An injected exception exercises catch/finally and compensation. Keep that test
for handled failures, then use a separate worker for abrupt termination:

1. Give the worker its own connection to the shared test database. Do not use a
   private `:memory:` database or a parent test transaction invisible to it.
2. Let the real writer signal after the relevant statement and before the next
   persistence step. Publish a complete marker atomically or use an IPC barrier;
   a fixed sleep is not evidence that the worker reached the boundary.
3. Bound the wait, reject bootstrap failure and require the worker to be alive
   before injecting process loss. On POSIX, verify the `SIGKILL` termination
   status. On other platforms record the actual termination mechanism and limits.
4. Reopen the database after the worker exits and assert the invariant, including
   durable related rows. Do not accept any nonzero exit as proof of a crash test.
5. Terminate remaining workers and clean up temporary state even if assertions
   fail. Keep the original failing run or a deliberately broken control.

If the guarantee covers every committed mutation, retain and inspect history.
After interrupting request A, let request B succeed and verify that A has not
become an unaudited committed version hidden behind B's correctly audited value.
A final-state assertion on B alone misses that failure.

## Coordinate Overlapping Requests

Use two requests with separate connections and observable barriers around the
contested boundary. Hold A at that boundary, start B and establish that B reached
its attempted write or lock acquisition; then release A. Bound both waits and
database lock timeouts, and propagate worker failures to the test process.

Assert the allowed durable outcomes and audit association for both requests.
Include failure of A after B succeeds when compensation could restore stale
state over B's committed value. Check that locks remain owned until the actual
outer commit, not merely a helper return or savepoint release. Avoid assertions
based solely on call order or a lucky scheduler interleaving.

## Report the Evidence at Its Actual Scope

Record the implementation revision, backend, tested boundary/interleaving,
commands and outcomes. Report unexecuted configurations as unverified. Run the
extension's functional suite through `Build/Scripts/runTests.sh -s functional`
with its required PHP/database settings; the repository's CI is authoritative.

A finite model can help explore orderings when that specific guarantee needs
it. Validate intended counterexamples and reachable successful operations, then
translate useful traces into implementation tests when that work is in scope.
Report model assumptions and bounds separately from runtime results; neither a
green model nor these tests provide a refinement proof of the PHP implementation.

## Sources

- [TYPO3 ConnectionPool and table mappings](https://api.typo3.org/main/classes/TYPO3-CMS-Core-Database-ConnectionPool.html)
- [Doctrine DBAL transaction nesting](https://www.doctrine-project.org/projects/doctrine-dbal/en/4.3/reference/transactions.html#transaction-nesting)
- [Python process termination and return codes](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.kill)
