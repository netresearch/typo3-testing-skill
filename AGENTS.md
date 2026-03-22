# TYPO3 Testing Skill

Agent harness for the TYPO3 testing skill repository.

## Repo Structure

```
├── skills/typo3-testing/             # Skill definition
│   ├── SKILL.md                      # Main skill instructions
│   ├── assets/                       # Template configs (PHPUnit, PHPStan, Rector, etc.)
│   ├── checkpoints.yaml              # Eval checkpoints
│   ├── references/                   # Detailed testing docs (21 reference files)
│   └── scripts/                      # Skill helper scripts
│       ├── setup-testing.sh          # Initialize test infrastructure
│       ├── generate-test.sh          # Generate test file scaffolds
│       └── validate-setup.sh         # Validate existing setup
├── agents/                           # Agent definitions
│   ├── test-generator.md             # Test generation agent
│   └── coverage-analyzer.md          # Coverage analysis agent
├── evals/                            # Evaluation suite
│   └── evals.json
├── Build/                            # Build tooling
│   ├── Scripts/                      # Utility scripts
│   └── hooks/                        # Git hooks (pre-commit, pre-push)
├── composer.json                     # Composer package (ai-agent-skill type)
├── docs/                             # Architecture and planning docs
│   └── ARCHITECTURE.md
└── scripts/                          # Harness scripts
    └── verify-harness.sh
```

## Commands

No build system scripts defined in `composer.json`. This is a content-only skill repo.

Key skill scripts (run from skill directory in target extension context):
- `scripts/setup-testing.sh [--with-e2e]` -- Initialize testing infrastructure
- `scripts/generate-test.sh <Type> <Class>` -- Generate test file scaffold
- `scripts/validate-setup.sh` -- Validate existing test setup

Test commands (run in target extension, not this repo):
- `Build/Scripts/runTests.sh -s unit` -- Unit tests
- `Build/Scripts/runTests.sh -s functional` -- Functional tests
- `Build/Scripts/runTests.sh -s phpstan` -- Static analysis
- `Build/Scripts/runTests.sh -s cgl` -- Coding guidelines

## Rules

- **runTests.sh is mandatory**: All Netresearch TYPO3 extensions must have `Build/Scripts/runTests.sh`
- **Coverage**: Unit tests required with 70%+ coverage; functional tests required for DB operations
- **Architecture tests**: phpat required for full scoring points
- **Verify tests**: Always verify a test fails before the fix and passes after
- **No composer.lock**: TYPO3 extensions should NOT commit composer.lock
- **CI authoritative**: CI is the authoritative source for test results, not local runs

## References

- [SKILL.md](skills/typo3-testing/SKILL.md) -- Main skill definition
- [Unit testing](skills/typo3-testing/references/unit-testing.md)
- [Functional testing](skills/typo3-testing/references/functional-testing.md)
- [E2E testing](skills/typo3-testing/references/e2e-testing.md)
- [Architecture testing](skills/typo3-testing/references/architecture-testing.md)
- [CI/CD integration](skills/typo3-testing/references/ci-cd.md)
- [CI debugging](skills/typo3-testing/references/ci-debugging.md)
- [Mutation testing](skills/typo3-testing/references/mutation-testing.md)
- [Quality tools](skills/typo3-testing/references/quality-tools.md)
- [Asset templates guide](skills/typo3-testing/references/asset-templates-guide.md)
- [Test generator agent](agents/test-generator.md)
- [Coverage analyzer agent](agents/coverage-analyzer.md)
