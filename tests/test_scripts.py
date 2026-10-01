#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Netresearch DTT GmbH
"""Behaviour tests for the shell scripts this repository ships.

Covered:

- skills/typo3-testing/scripts/setup-testing.sh, generate-test.sh and
  validate-setup.sh, run against a small TYPO3 extension layout;
- the TT-105 and TT-106 script checkpoints in skills/typo3-testing/checkpoints.yaml,
  and a guard that no checkpoint uses the `expected:` field;
- Build/Scripts/validate-skill.sh with the Build/hooks/pre-commit hook that
  calls it, Build/Scripts/check-plugin-version.sh with the Build/hooks/pre-push
  hook that calls it, and scripts/verify-harness.sh.

The script tests build their input in a temporary directory, run the script as
a subprocess and check its exit code, its output and the files it wrote; the
`expected:` guard reads checkpoints.yaml directly.
`composer`, `vendor/bin/codecept` and `docker` are replaced by stubs that
record their arguments, so no test installs packages or talks to a daemon.
generate-test.sh reads composer.json with `php -r`, so these tests need `php`
on PATH (the GitHub-hosted ubuntu-latest runner has it).

Standard library only; run with ``python3 tests/test_scripts.py``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "typo3-testing"
ASSETS = SKILL / "assets"
SETUP = SKILL / "scripts" / "setup-testing.sh"
GENERATE = SKILL / "scripts" / "generate-test.sh"
VALIDATE_SETUP = SKILL / "scripts" / "validate-setup.sh"
CHECKPOINTS = SKILL / "checkpoints.yaml"
VALIDATE_SKILL = ROOT / "Build" / "Scripts" / "validate-skill.sh"
PRE_COMMIT = ROOT / "Build" / "hooks" / "pre-commit"
CHECK_VERSION = ROOT / "Build" / "Scripts" / "check-plugin-version.sh"
PRE_PUSH = ROOT / "Build" / "hooks" / "pre-push"
VERIFY_HARNESS = ROOT / "scripts" / "verify-harness.sh"

BASH = shutil.which("bash") or "/bin/bash"

ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}
# verify-harness.sh switches to annotation output under GitHub Actions, and
# validate-skill.sh takes the expected composer name from GITHUB_REPOSITORY.
ENV.pop("GITHUB_ACTIONS", None)
ENV.pop("GITHUB_REPOSITORY", None)

COMPOSER_WITH_NAMESPACE = '{"autoload": {"psr-4": {"Vendor\\\\Ext\\\\": "Classes/"}}}\n'

# A stub that appends its name and arguments to $STUB_LOG and succeeds.
STUB = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "$STUB_LOG"\n'


def run(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, env=env or ENV, capture_output=True, text=True, check=False
    )


def write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def checkpoint_script(checkpoint_id: str) -> str:
    """Return the `command: |` body of one checkpoint, dedented.

    A small reader for the one shape this needs (a literal block under a
    `- id:` entry), so the suite stays standard-library only.
    """
    lines = CHECKPOINTS.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"  - id: {checkpoint_id}")
    body: list[str] = []
    in_block = False
    for line in lines[start + 1 :]:
        if line.startswith("  - id:"):
            break
        if line == "    command: |":
            in_block = True
            continue
        if in_block:
            if line.startswith("      ") or line == "":
                body.append(line[6:])
            else:
                break
    if not body:
        raise AssertionError(f"{checkpoint_id} has no literal command block")
    return "\n".join(body) + "\n"


class TempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.project = self.tmp / "project"
        self.project.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()


class SetupTestingTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.log = self.tmp / "stub.log"
        self.log.write_text("", encoding="utf-8")
        bindir = self.tmp / "bin"
        write(bindir / "composer", STUB, 0o755)
        write(self.project / "vendor" / "bin" / "codecept", STUB, 0o755)
        self.env = {
            **ENV,
            "PATH": f"{bindir}{os.pathsep}{ENV['PATH']}",
            "STUB_LOG": str(self.log),
        }

    def setup(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([BASH, str(SETUP), *args], cwd=self.project, env=self.env)

    def calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines()

    def test_missing_composer_json_fails(self) -> None:
        result = self.setup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("composer.json not found in current directory", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_fresh_extension_gets_dependencies_configs_and_directories(self) -> None:
        write(self.project / "composer.json", "{}\n")
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            self.calls(),
            [
                "composer require --dev typo3/testing-framework:^8.0 || ^9.0 --no-update",
                "composer require --dev phpunit/phpunit:^10.5 || ^11.0 --no-update",
                "composer update --no-progress",
            ],
        )
        for directory in (
            "Tests/Unit",
            "Tests/Functional/Fixtures",
            "Build/phpunit",
            "Build/Scripts",
        ):
            self.assertTrue((self.project / directory).is_dir(), directory)
        for name in (
            "UnitTests.xml",
            "FunctionalTests.xml",
            "FunctionalTestsBootstrap.php",
        ):
            self.assertEqual(
                (self.project / "Build" / "phpunit" / name).read_bytes(),
                (ASSETS / name).read_bytes(),
                name,
            )
        for directory in ("Tests/Unit", "Tests/Functional"):
            self.assertEqual(
                (self.project / directory / "AGENTS.md").read_bytes(),
                (ASSETS / "AGENTS.md").read_bytes(),
            )
        self.assertIn("Add these scripts to your composer.json", result.stdout)
        self.assertIn(
            '"ci:test:php:unit": "phpunit -c Build/phpunit/UnitTests.xml"',
            result.stdout,
        )
        self.assertIn("Skipping acceptance testing setup", result.stdout)
        self.assertFalse((self.project / "codeception.yml").exists())

    def test_existing_dependencies_and_files_are_kept(self) -> None:
        write(
            self.project / "composer.json",
            '{"require-dev": {"typo3/testing-framework": "^9", "phpunit/phpunit": "^11"},'
            ' "scripts": {"ci:test:php:unit": "phpunit"}}\n',
        )
        write(self.project / "Build" / "phpunit" / "UnitTests.xml", "own\n")
        write(self.project / "Tests" / "Unit" / "AGENTS.md", "own\n")
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), ["composer update --no-progress"])
        self.assertIn("typo3/testing-framework already present", result.stdout)
        self.assertIn("UnitTests.xml already exists (skipped)", result.stdout)
        self.assertIn("Test scripts already configured", result.stdout)
        self.assertEqual(
            (self.project / "Build" / "phpunit" / "UnitTests.xml").read_text(), "own\n"
        )
        self.assertEqual(
            (self.project / "Tests" / "Unit" / "AGENTS.md").read_text(), "own\n"
        )

    def test_acceptance_option_sets_up_codeception(self) -> None:
        write(self.project / "composer.json", "{}\n")
        result = self.setup("-a")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "composer require --dev codeception/codeception codeception/module-webdriver"
            " --no-update",
            self.calls(),
        )
        self.assertEqual(self.calls()[-1], "codecept bootstrap")
        self.assertTrue((self.project / "Tests" / "Acceptance").is_dir())
        self.assertEqual(
            (self.project / "Build" / "docker-compose.yml").read_bytes(),
            (ASSETS / "docker" / "docker-compose.yml").read_bytes(),
        )
        self.assertEqual(
            (self.project / "codeception.yml").read_bytes(),
            (ASSETS / "docker" / "codeception.yml").read_bytes(),
        )

    def test_unknown_options_are_rejected(self) -> None:
        write(self.project / "composer.json", "{}\n")
        for option in ("-x", "--with-e2e"):
            with self.subTest(option=option):
                result = self.setup(option)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Usage:", result.stdout)
        self.assertEqual(self.calls(), [])


class GenerateTestTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        write(self.project / "composer.json", COMPOSER_WITH_NAMESPACE)
        (self.project / "Tests").mkdir()

    def generate(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([BASH, str(GENERATE), *args], cwd=self.project)

    def assert_php_parses(self, path: Path) -> None:
        result = run(["php", "-l", str(path)], cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.tmp)) for p in self.tmp.rglob("*") if p.is_file()
        )

    def test_missing_arguments_print_usage(self) -> None:
        result = self.generate("unit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("acceptance Login\n", result.stdout)

    def test_invalid_type_is_rejected(self) -> None:
        result = self.generate("integration", "Foo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid test type 'integration'", result.stdout)

    def test_class_names_that_are_not_identifiers_are_rejected(self) -> None:
        before = self.files()
        for name in ("../../Escaped", "Domain/Model/Foo", "1Foo", "Foo-Bar", "Foo;"):
            with self.subTest(name=name):
                result = self.generate("unit", name)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"Invalid class name '{name}'", result.stdout)
        self.assertEqual(self.files(), before)

    def test_missing_tests_directory_fails(self) -> None:
        (self.project / "Tests").rmdir()
        result = self.generate("unit", "Foo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Run setup-testing.sh first", result.stdout)

    def test_missing_namespace_fails(self) -> None:
        write(
            self.project / "composer.json",
            '{"autoload": {"psr-4": {"X\\\\": "src/"}}}\n',
        )
        result = self.generate("unit", "Foo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not determine namespace", result.stdout)

    def test_unit_test(self) -> None:
        result = self.generate("unit", "EmailValidator")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.project / "Tests" / "Unit" / "EmailValidatorTest.php"
        content = path.read_text(encoding="utf-8")
        self.assertIn("namespace Vendor\\Ext\\Tests\\Unit;", content)
        self.assertIn("use PHPUnit\\Framework\\Attributes\\Test;", content)
        self.assertIn("use Vendor\\Ext\\EmailValidator;", content)
        self.assertIn("final class EmailValidatorTest extends UnitTestCase", content)
        self.assertIn("    #[Test]\n    public function canBeInstantiated", content)
        self.assertNotIn("@test", content)
        self.assert_php_parses(path)

    def test_functional_test_creates_the_fixture_directory(self) -> None:
        result = self.generate("functional", "ProductRepository")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.project / "Tests" / "Functional" / "ProductRepositoryTest.php"
        content = path.read_text(encoding="utf-8")
        self.assertIn("extends FunctionalTestCase", content)
        self.assertIn("    #[Test]\n", content)
        self.assert_php_parses(path)
        fixture = (
            self.project / "Tests" / "Functional" / "Fixtures" / "ProductRepository.csv"
        )
        self.assertEqual(
            fixture.read_text(encoding="utf-8"), "# Fixture for ProductRepositoryTest\n"
        )

    def test_a_subject_named_test_does_not_clash_with_the_attribute(self) -> None:
        # PHP class names are case-insensitive: `use ...\\Attributes\\Test;` and
        # `use Vendor\\Ext\\Test;` in one file is a compile error.
        for kind, name in (("unit", "Test"), ("functional", "test")):
            with self.subTest(kind=kind, name=name):
                result = self.generate(kind, name)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                path = self.project / "Tests" / kind.capitalize() / f"{name}Test.php"
                content = path.read_text(encoding="utf-8")
                self.assertIn(
                    "use PHPUnit\\Framework\\Attributes\\Test as TestAttribute;",
                    content,
                )
                self.assertIn("    #[TestAttribute]\n", content)
                self.assert_php_parses(path)

    def test_acceptance_test(self) -> None:
        result = self.generate("acceptance", "Login")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.project / "Tests" / "Acceptance" / "LoginCest.php"
        self.assertIn("final class LoginCest\n", path.read_text(encoding="utf-8"))
        self.assert_php_parses(path)

    def test_existing_test_is_not_overwritten(self) -> None:
        path = self.project / "Tests" / "Unit" / "FooTest.php"
        write(path, "own\n")
        result = self.generate("unit", "Foo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Test file already exists", result.stdout)
        self.assertEqual(path.read_text(encoding="utf-8"), "own\n")


class ValidateSetupTest(TempDirTestCase):
    def validate(self, docker: str | None) -> subprocess.CompletedProcess[str]:
        """Run with a PATH that holds only what the script needs.

        docker: None for "not installed", otherwise the exit code of `docker ps`.
        """
        bindir = self.tmp / "bin"
        bindir.mkdir(exist_ok=True)
        for tool in ("grep", "dirname"):
            target = bindir / tool
            if not target.exists():
                target.symlink_to(shutil.which(tool) or f"/usr/bin/{tool}")
        if docker is not None:
            write(bindir / "docker", f"#!{BASH}\nexit {docker}\n", 0o755)
        env = {**ENV, "PATH": str(bindir)}
        return run([BASH, str(VALIDATE_SETUP)], cwd=self.project, env=env)

    def complete_setup(self) -> None:
        write(
            self.project / "composer.json",
            '{"require-dev": {"typo3/testing-framework": "^9", "phpunit/phpunit": "^11"}}\n',
        )
        for name in (
            "UnitTests.xml",
            "FunctionalTests.xml",
            "FunctionalTestsBootstrap.php",
        ):
            write(self.project / "Build" / "phpunit" / name, "x\n")
        (self.project / "Tests" / "Functional" / "Fixtures").mkdir(parents=True)
        for directory in ("Tests/Unit", "Tests/Functional"):
            write(self.project / directory / "AGENTS.md", "x\n")

    def test_empty_directory_reports_every_finding(self) -> None:
        result = self.validate(docker=None)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[5/5] Checking Docker availability", result.stdout)
        self.assertIn("4 errors found", result.stdout)
        self.assertIn("6 warnings found", result.stdout)
        self.assertIn(f"{SETUP.parent}/setup-testing.sh", result.stdout)

    def test_missing_dependencies_are_errors(self) -> None:
        self.complete_setup()
        write(self.project / "composer.json", "{}\n")
        result = self.validate(docker="0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("typo3/testing-framework missing", result.stdout)
        self.assertIn("phpunit/phpunit missing", result.stdout)
        self.assertIn("2 errors found", result.stdout)

    def test_complete_setup_passes(self) -> None:
        self.complete_setup()
        result = self.validate(docker="0")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("All checks passed!", result.stdout)
        self.assertIn(f"{GENERATE} unit MyClass", result.stdout)

    def test_warnings_alone_pass(self) -> None:
        self.complete_setup()
        for docker, message in (
            (None, "Docker not installed"),
            ("1", "Docker daemon not running"),
        ):
            with self.subTest(docker=docker):
                result = self.validate(docker=docker)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn(message, result.stdout)
                self.assertIn("1 warnings found", result.stdout)


class CheckpointTT105Test(TempDirTestCase):
    """TT-105: the higher of minCoveredMsi and minMsi is 90 or more."""

    def check(self, body: str) -> subprocess.CompletedProcess[str]:
        write(self.project / "infection.json5", body)
        script = self.tmp / "tt105.sh"
        script.write_text(checkpoint_script("TT-105"), encoding="utf-8")
        return run([BASH, str(script)], cwd=self.project)

    def test_low_threshold_with_space_before_the_colon_fails(self) -> None:
        # JSON5 allows whitespace between a key and its colon.
        result = self.check('{\n    "minMsi" : 70,\n}\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("threshold is 70", result.stdout)
        self.assertIn("minMsi=70", result.stdout)

    def test_high_threshold_with_space_before_the_colon_passes(self) -> None:
        result = self.check('{\n    "minMsi" : 95,\n}\n')
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_covered_msi_alone_passes(self) -> None:
        # The shape the skill recommends: no minMsi, minCoveredMsi gates.
        result = self.check('{\n    "minCoveredMsi" : 90,\n}\n')
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_low_covered_msi_alone_fails(self) -> None:
        result = self.check('{\n    "minCoveredMsi": 80,\n}\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("threshold is 80", result.stdout)
        self.assertIn("minMsi=unset", result.stdout)

    def test_the_higher_threshold_is_judged(self) -> None:
        # Without --with-uncovered both compare against the same score, so
        # the higher one gates; a passing minMsi must not be lost.
        result = self.check('{\n    "minMsi": 92,\n    "minCoveredMsi": 85,\n}\n')
        self.assertEqual(result.returncode, 0, result.stdout)
        result = self.check('{\n    "minMsi": 70,\n    "minCoveredMsi": 80,\n}\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("threshold is 80", result.stdout)

    def test_no_threshold_fails(self) -> None:
        result = self.check('{\n    "timeout": 10,\n}\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("declares neither minCoveredMsi nor minMsi", result.stdout)


class CheckpointTT106Test(TempDirTestCase):
    """TT-106: infection.json5 and infection-full.json5 agree on thresholds."""

    def check(self) -> subprocess.CompletedProcess[str]:
        # The assessment runner runs a multi-line checkpoint as a bash script
        # and judges it by its exit status alone.
        script = self.tmp / "tt106.sh"
        script.write_text(checkpoint_script("TT-106"), encoding="utf-8")
        return run([BASH, str(script)], cwd=self.project)

    def config(self, name: str, msi: int | None) -> None:
        line = f'    "minMsi": {msi},\n' if msi is not None else ""
        write(self.project / name, "{\n" + line + '    "timeout": 10,\n}\n')

    def test_different_thresholds_fail(self) -> None:
        self.config("infection.json5", 70)
        self.config("infection-full.json5", 90)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "minMsi is 70 in infection.json5 and 90 in infection-full.json5",
            result.stdout,
        )

    def test_whitespace_before_the_colon_is_read(self) -> None:
        # JSON5 allows whitespace between a key and its colon.
        write(self.project / "infection.json5", '{\n    "minMsi" : 70,\n}\n')
        self.config("infection-full.json5", 90)
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("minMsi is 70 in infection.json5", result.stdout)

    def test_equal_thresholds_pass(self) -> None:
        self.config("infection.json5", 85)
        self.config("infection-full.json5", 85)
        self.assertEqual(self.check().returncode, 0)

    def test_different_covered_thresholds_fail(self) -> None:
        # Configs that follow the skill declare only minCoveredMsi.
        write(self.project / "infection.json5", '{\n    "minCoveredMsi": 80,\n}\n')
        write(
            self.project / "infection-full.json5", '{\n    "minCoveredMsi" : 90,\n}\n'
        )
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "minCoveredMsi is 80 in infection.json5 and 90 in infection-full.json5",
            result.stdout,
        )

    def test_equal_covered_thresholds_pass(self) -> None:
        write(self.project / "infection.json5", '{\n    "minCoveredMsi": 85,\n}\n')
        write(self.project / "infection-full.json5", '{\n    "minCoveredMsi": 85,\n}\n')
        self.assertEqual(self.check().returncode, 0)

    def test_nothing_to_compare_passes(self) -> None:
        self.assertEqual(self.check().returncode, 0)
        self.config("infection.json5", 70)
        self.assertEqual(self.check().returncode, 0)
        self.config("infection-full.json5", None)
        self.assertEqual(self.check().returncode, 0)

    def test_no_checkpoint_relies_on_expected(self) -> None:
        # The runner never reads `expected:`; a check that needs it cannot fail.
        keys = [
            line
            for line in CHECKPOINTS.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith("expected:")
        ]
        self.assertEqual(keys, [])


class ValidateSkillTest(TempDirTestCase):
    def skill_repo(self, body_lines: int = 20, extra_front_matter: str = "") -> None:
        body = "".join(
            f"Line {i} with several words in it.\n" for i in range(body_lines)
        )
        write(
            self.project / "skills" / "demo" / "SKILL.md",
            "---\n"
            "# SPDX-License-Identifier: CC-BY-SA-4.0\n"
            "name: demo\n"
            f'description: "Use when testing the validator."\n{extra_front_matter}'
            "---\n\n# Demo\n\n" + body,
        )
        write(
            self.project / "README.md", "# Demo\n\nBy Netresearch.\n\n## Installation\n"
        )
        write(self.project / ".gitignore", "vendor/\n")
        write(self.project / "LICENSE-MIT", "MIT\n")
        write(self.project / "LICENSE-CC-BY-SA-4.0", "CC\n")
        write(self.project / ".github" / "workflows" / "release.yml", "name: Release\n")
        write(
            self.project / "composer.json",
            '{"name": "netresearch/demo-skill", "type": "ai-agent-skill",'
            ' "require": {"netresearch/composer-agent-skill-plugin": "*"},'
            ' "extra": {"ai-agent-skill": "skills/demo/SKILL.md"}}\n',
        )
        write(
            self.project / ".claude-plugin" / "plugin.json",
            '{"name": "demo", "skills": ["./skills/demo"],'
            ' "author": {"url": "https://www.netresearch.de/"}}\n',
        )

    def validate(self) -> subprocess.CompletedProcess[str]:
        return run([BASH, str(VALIDATE_SKILL), str(self.project)], cwd=self.tmp)

    def test_valid_repository_passes(self) -> None:
        self.skill_repo()
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("SKILL.md body is", result.stdout)
        self.assertIn("Frontmatter has only name + description", result.stdout)

    def test_long_prose_under_300_body_lines_passes(self) -> None:
        # 250 lines of seven words: far above the former 500-word cap.
        self.skill_repo(body_lines=250)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Warnings: \x1b[1;33m0", result.stdout)

    def test_body_over_300_lines_warns(self) -> None:
        self.skill_repo(body_lines=400)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("past 300", result.stdout)

    def test_body_over_500_lines_fails(self) -> None:
        self.skill_repo(body_lines=520)
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("(spec recommends under 500)", result.stdout)

    def test_extra_front_matter_field_fails(self) -> None:
        self.skill_repo(extra_front_matter="version: 1.0.0\n")
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Frontmatter has disallowed fields: version", result.stdout)

    def test_missing_files_fail(self) -> None:
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("SKILL.md not found", result.stdout)
        self.assertIn("composer.json not found", result.stdout)

    def test_pre_commit_hook_validates_the_repository_root(self) -> None:
        self.skill_repo(body_lines=520)
        for cmd in (["git", "init", "-q"], ["git", "add", "."]):
            self.assertEqual(run(cmd, cwd=self.project).returncode, 0)
        result = run([BASH, str(PRE_COMMIT)], cwd=self.project / "skills")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Validating skill repository: {self.project}", result.stdout)
        self.assertIn("(spec recommends under 500)", result.stdout)


class CheckPluginVersionTest(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        write(
            self.project / ".claude-plugin" / "plugin.json",
            '{"name": "demo", "version": "1.2.3"}\n',
        )
        for cmd in (
            ["git", "init", "-q"],
            ["git", "add", "."],
            ["git", "commit", "-q", "-m", "init"],
        ):
            result = run(cmd, cwd=self.project)
            self.assertEqual(result.returncode, 0, result.stderr)

    def tag(self, name: str) -> None:
        result = run(["git", "tag", name], cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)

    def check(self) -> subprocess.CompletedProcess[str]:
        return run([BASH, str(CHECK_VERSION)], cwd=self.project)

    def test_untagged_head_passes(self) -> None:
        self.assertEqual(self.check().returncode, 0)

    def test_matching_tag_passes(self) -> None:
        self.tag("v1.2.3")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_matching_tag_without_prefix_passes(self) -> None:
        self.tag("1.2.3")
        self.assertEqual(self.check().returncode, 0)

    def test_mismatching_tag_fails(self) -> None:
        self.tag("v1.2.4")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "version (1.2.3) does not match any semver tag at HEAD", result.stderr
        )
        self.assertIn("1.2.4", result.stderr)

    def test_non_semver_tag_is_ignored(self) -> None:
        self.tag("release-candidate")
        self.assertEqual(self.check().returncode, 0)

    def test_pre_push_hook_runs_the_check(self) -> None:
        self.tag("v2.0.0")
        result = run([BASH, str(PRE_PUSH)], cwd=self.project)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match any semver tag at HEAD", result.stderr)


class VerifyHarnessTest(TempDirTestCase):
    def verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(
            [BASH, str(VERIFY_HARNESS), "--format=text", *args], cwd=self.project
        )

    def complete_level2(self) -> None:
        write(
            self.project / "AGENTS.md",
            "# Demo\n\n## Commands\n\nSee [docs](docs/ARCHITECTURE.md).\n",
        )
        write(self.project / "docs" / "ARCHITECTURE.md", "# Architecture\n")
        write(
            self.project / ".github" / "workflows" / "harness-verify.yml",
            "name: Harness\n",
        )

    def test_empty_directory_fails(self) -> None:
        result = self.verify("--level=1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("AGENTS.md missing at repo root", result.stdout)
        self.assertIn("Summary: Level 1 NONE | 4 error(s), 0 warning(s)", result.stdout)

    def test_complete_level2_passes(self) -> None:
        self.complete_level2()
        result = self.verify("--level=2")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "Summary: Level 2 COMPLETE | 0 error(s), 0 warning(s)", result.stdout
        )

    def test_complete_level3_without_git_passes(self) -> None:
        # A local PR template keeps check_pr_template from querying the GitHub API.
        self.complete_level2()
        write(self.project / ".github" / "pull_request_template.md", "## Summary\n")
        write(self.project / ".envrc", "git config core.hooksPath Build/hooks\n")
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Git hooks auto-setup via .envrc", result.stdout)
        self.assertIn(
            "Summary: Level 3 COMPLETE | 0 error(s), 0 warning(s)", result.stdout
        )

    def test_long_agents_md_fails(self) -> None:
        self.complete_level2()
        write(self.project / "AGENTS.md", "# Demo\n\n## Commands\n" + "line\n" * 150)
        result = self.verify("--level=1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("(should be under 150)", result.stdout)

    def test_broken_reference_is_a_warning(self) -> None:
        self.complete_level2()
        write(self.project / "AGENTS.md", "# Demo\n\n## Commands\n\n[x](missing.md)\n")
        result = self.verify("--check=refs")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("missing.md not found", result.stdout)

    def test_undocumented_composer_script_is_a_warning(self) -> None:
        self.complete_level2()
        write(
            self.project / "AGENTS.md", "# Demo\n\n## Commands\n\n`composer ci:test`\n"
        )
        write(self.project / "composer.json", '{"scripts": {}}\n')
        result = self.verify("--check=commands")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(
            "composer ci:test: no matching composer.json script", result.stdout
        )

    def test_github_format_emits_annotations(self) -> None:
        result = run(
            [BASH, str(VERIFY_HARNESS), "--format=github", "--level=1"],
            cwd=self.project,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "::error file=AGENTS.md::AGENTS.md missing at repo root", result.stdout
        )

    def test_invalid_arguments_are_rejected(self) -> None:
        self.assertEqual(self.verify("--level=4").returncode, 1)
        self.assertEqual(self.verify("--check=bogus").returncode, 1)
        self.assertEqual(self.verify("--bogus").returncode, 1)


if __name__ == "__main__":
    unittest.main()
