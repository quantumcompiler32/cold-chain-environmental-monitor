"""Load, validate, and apply deterministic ByteSmart vault rules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib


NOTE_TYPES = frozenset(
    {
        "project",
        "index",
        "source",
        "topic",
        "work-item",
        "finding",
        "decision",
        "deliverable",
        "review",
    }
)
RULES_VERSION = 1
OVERRIDES_VERSION = 1


class RuleValidationError(ValueError):
    """Raised when the deterministic categorization rules are not usable."""


@dataclass(frozen=True)
class Rule:
    name: str
    branch: str
    note_type: str
    filename_contains: tuple[str, ...] = ()
    path_contains: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    headings_contains: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManualOverride:
    reference: str
    branch: str
    note_type: str


@dataclass(frozen=True)
class VaultRules:
    version: int
    branches: tuple[str, ...]
    rules: tuple[Rule, ...]
    inbox_folder: str


@dataclass(frozen=True)
class VaultOverrides:
    overrides: tuple[ManualOverride, ...]


@dataclass(frozen=True)
class Classification:
    branch: str | None
    note_type: str
    reason: str
    is_inbox: bool = False


def _as_strings(value: object, field: str, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise RuleValidationError(f"{location}.{field} must be a list of non-empty strings")
    return tuple(item.strip() for item in value)


def _required_string(value: object, field: str, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleValidationError(f"{location}.{field} must be a non-empty string")
    return value.strip()


def _required_integer(value: object, field: str, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuleValidationError(f"{location}.{field} must be an integer")
    return value


def _optional_strings(value: object, field: str, location: str) -> tuple[str, ...]:
    if value is None:
        return ()
    return _as_strings(value, field, location)


def _load_rule(raw_rule: object, branches: tuple[str, ...], position: int) -> Rule:
    location = f"rule[{position}]"
    if not isinstance(raw_rule, dict):
        raise RuleValidationError(f"{location} must be a table")

    name = _required_string(raw_rule.get("name"), "name", location)
    branch = _required_string(raw_rule.get("branch"), "branch", location)
    note_type = _required_string(raw_rule.get("note_type"), "note_type", location)
    if branch not in branches:
        raise RuleValidationError(f"{location}.branch targets unknown branch: {branch}")
    if note_type not in NOTE_TYPES:
        raise RuleValidationError(f"{location}.note_type is not supported: {note_type}")

    rule = Rule(
        name=name,
        branch=branch,
        note_type=note_type,
        filename_contains=_optional_strings(raw_rule.get("filename_contains"), "filename_contains", location),
        path_contains=_optional_strings(raw_rule.get("path_contains"), "path_contains", location),
        extensions=_optional_strings(raw_rule.get("extensions"), "extensions", location),
        headings_contains=_optional_strings(raw_rule.get("headings_contains"), "headings_contains", location),
    )
    if not any((rule.filename_contains, rule.path_contains, rule.extensions, rule.headings_contains)):
        raise RuleValidationError(f"{location} must include at least one matching condition")
    return rule


def _matcher_signature(rule: Rule) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(item.lower() for item in rule.filename_contains),
        tuple(item.lower() for item in rule.path_contains),
        tuple(item.lower() for item in rule.extensions),
        tuple(item.lower() for item in rule.headings_contains),
    )


def load_rules(path: Path) -> VaultRules:
    """Load a validated TOML rule file without touching vault content."""
    with path.open("rb") as rules_file:
        raw = tomllib.load(rules_file)

    version = _required_integer(raw.get("version"), "version", "root")
    if version != RULES_VERSION:
        raise RuleValidationError(f"root.version must be {RULES_VERSION}")
    inbox_folder = _required_string(raw.get("inbox_folder"), "inbox_folder", "root")
    branches = _as_strings(raw.get("branches"), "branches", "root")
    if len(set(branches)) != len(branches):
        raise RuleValidationError("root.branches must not contain duplicates")
    if inbox_folder in branches:
        raise RuleValidationError("root.inbox_folder must not be a visible branch")

    raw_rules = raw.get("rule", [])
    if not isinstance(raw_rules, list):
        raise RuleValidationError("root.rule must be a list of tables")
    rules = tuple(_load_rule(raw_rule, branches, position) for position, raw_rule in enumerate(raw_rules, start=1))
    names = [rule.name for rule in rules]
    if len(set(names)) != len(names):
        raise RuleValidationError("rule names must be unique")
    matcher_targets: dict[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]], Rule] = {}
    for rule in rules:
        signature = _matcher_signature(rule)
        existing = matcher_targets.get(signature)
        if existing and (existing.branch, existing.note_type) != (rule.branch, rule.note_type):
            raise RuleValidationError(
                f"rule {rule.name!r} conflicts with {existing.name!r}: identical match conditions have different targets"
            )
        matcher_targets[signature] = rule
    return VaultRules(version=version, branches=branches, rules=rules, inbox_folder=inbox_folder)


def load_overrides(path: Path, rules: VaultRules | None = None) -> VaultOverrides:
    """Load exact manual source decisions without changing source files."""
    if not path.exists():
        return VaultOverrides(overrides=())
    with path.open("rb") as overrides_file:
        raw = tomllib.load(overrides_file)
    version = _required_integer(raw.get("version"), "version", "root")
    if version != OVERRIDES_VERSION:
        raise RuleValidationError(f"root.version must be {OVERRIDES_VERSION}")
    raw_overrides = raw.get("override", [])
    if not isinstance(raw_overrides, list):
        raise RuleValidationError("root.override must be a list of tables")
    overrides: list[ManualOverride] = []
    for position, raw_override in enumerate(raw_overrides, start=1):
        location = f"override[{position}]"
        if not isinstance(raw_override, dict):
            raise RuleValidationError(f"{location} must be a table")
        reference = str(Path(_required_string(raw_override.get("reference"), "reference", location)).expanduser().resolve())
        branch = _required_string(raw_override.get("branch"), "branch", location)
        note_type = _required_string(raw_override.get("note_type"), "note_type", location)
        if rules and branch not in rules.branches:
            raise RuleValidationError(f"{location}.branch targets unknown branch: {branch}")
        if note_type not in NOTE_TYPES:
            raise RuleValidationError(f"{location}.note_type is not supported: {note_type}")
        overrides.append(ManualOverride(reference=reference, branch=branch, note_type=note_type))
    references = [override.reference for override in overrides]
    if len(set(references)) != len(references):
        raise RuleValidationError("manual override references must be unique")
    return VaultOverrides(overrides=tuple(overrides))


def _contains_any(value: str, expected: tuple[str, ...]) -> bool:
    return not expected or any(item.lower() in value for item in expected)


def _matches(rule: Rule, path: Path, headings: tuple[str, ...]) -> bool:
    filename = path.name.lower()
    full_path = path.as_posix().lower()
    suffix = path.suffix.lower()
    combined_headings = "\n".join(headings).lower()
    return (
        _contains_any(filename, rule.filename_contains)
        and _contains_any(full_path, rule.path_contains)
        and (not rule.extensions or suffix in {extension.lower() for extension in rule.extensions})
        and _contains_any(combined_headings, rule.headings_contains)
    )


def classify(
    path: Path,
    rules: VaultRules,
    *,
    headings: tuple[str, ...] = (),
    explicit_branch: str | None = None,
    explicit_note_type: str | None = None,
    overrides: VaultOverrides | None = None,
    override_reference: str | None = None,
) -> Classification:
    """Classify one item using explicit metadata before deterministic rules."""
    matching_rule = next((rule for rule in rules.rules if _matches(rule, path, headings)), None)
    if explicit_branch is not None and explicit_branch not in rules.branches:
        return Classification(
            branch=None,
            note_type="review",
            reason=f"unknown explicit branch: {explicit_branch}",
            is_inbox=True,
        )
    if explicit_note_type is not None and explicit_note_type not in NOTE_TYPES:
        return Classification(
            branch=None,
            note_type="review",
            reason=f"unsupported explicit note type: {explicit_note_type}",
            is_inbox=True,
        )
    if explicit_branch is not None or explicit_note_type is not None:
        branch = explicit_branch or (matching_rule.branch if matching_rule else None)
        note_type = explicit_note_type or (matching_rule.note_type if matching_rule else "review")
        if branch is None:
            return Classification(
                branch=None,
                note_type="review",
                reason="explicit metadata needs a branch or matching rule",
                is_inbox=True,
            )
        return Classification(branch=branch, note_type=note_type, reason="explicit metadata")
    lookup_reference = override_reference or str(path)
    matching_override = next(
        (override for override in (overrides.overrides if overrides else ()) if override.reference == lookup_reference), None
    )
    if matching_override:
        return Classification(
            branch=matching_override.branch,
            note_type=matching_override.note_type,
            reason="manual override",
        )
    if matching_rule:
        return Classification(
            branch=matching_rule.branch,
            note_type=matching_rule.note_type,
            reason=f"rule: {matching_rule.name}",
        )
    return Classification(branch=None, note_type="review", reason="no deterministic rule matched", is_inbox=True)


def main(argv: list[str] | None = None) -> int:
    """Validate a rule file without scanning or changing the vault."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-rules", type=Path, metavar="PATH", required=True)
    args = parser.parse_args(argv)
    try:
        rules = load_rules(args.check_rules)
    except (OSError, tomllib.TOMLDecodeError, RuleValidationError) as error:
        print(f"Rules invalid: {error}", file=sys.stderr)
        return 1
    branch_label = "branch" if len(rules.branches) == 1 else "branches"
    rule_label = "rule" if len(rules.rules) == 1 else "rules"
    print(f"Rules valid: {len(rules.branches)} {branch_label}, {len(rules.rules)} {rule_label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
