"""
Rule Loader - Load and inject rules into agent context.

This module handles loading rule files from rules/ directory and injecting them
into agent LLM context as mandatory constraints.
"""
from pathlib import Path
from typing import List, Dict
from config.settings import get_settings


class RuleLoadError(Exception):
    """Error loading rule file."""
    pass


def load_rule(rule_path: str) -> str:
    """
    Load a single rule file content.

    Args:
        rule_path: Path relative to rules/ directory (e.g., "common/security.md")

    Returns:
        Rule file content as string

    Raises:
        RuleLoadError: If file not found
    """
    settings = get_settings()
    rules_dir = Path(settings.RULES_DIR)
    rule_file = rules_dir / rule_path

    if not rule_file.exists():
        raise RuleLoadError(
            f"Rule file not found: {rule_path}. "
            f"Looked in: {rules_dir}"
        )

    return rule_file.read_text()


def get_relevant_rules(agent_name: str) -> List[str]:
    """
    Get list of relevant rules for an agent.

    Args:
        agent_name: Name of agent (e.g., "aco-pm")

    Returns:
        List of rule paths to inject

    Mapping:
        - All agents get common rules
        - dev gets git-workflow and coding-standards
        - qa gets testing
        - architect gets security (CRITICAL)
    """
    # Common rules for all agents
    rules = [
        "common/coding-standards.md",
    ]

    # Role-specific rules
    if agent_name == "aco-pm":
        # PM: general standards
        pass  # No additional rules beyond common

    elif agent_name == "aco-planner":
        # Planner: general standards
        pass  # No additional rules beyond common

    elif agent_name == "aco-architect":
        # Architect: CRITICAL to review security
        rules.extend([
            "common/security.md",  # Security review is architect's job
        ])

    elif agent_name == "aco-dev":
        # Dev: git workflow and coding standards
        rules.extend([
            "common/git-workflow.md",
            "common/coding-standards.md",
        ])

    elif agent_name == "aco-qa":
        # QA: testing requirements
        rules.extend([
            "common/testing.md",
        ])

    elif agent_name == "aco-human":
        # Human: no rules needed (pure routing)
        rules = []

    return rules


def load_multiple_rules(rule_paths: List[str]) -> Dict[str, str]:
    """
    Load multiple rule files.

    Args:
        rule_paths: List of rule paths

    Returns:
        Dictionary mapping rule_path to content

    Raises:
        RuleLoadError: If any file not found
    """
    rules = {}
    for path in rule_paths:
        try:
            content = load_rule(path)
            rules[path] = content
        except RuleLoadError as e:
            # Log but continue loading others
            import logging
            logging.warning(f"Failed to load rule {path}: {e}")

    return rules


def validate_rules_directory() -> Dict:
    """
    Validate that required rule files exist.

    Returns:
        Dictionary with validation results:
        - valid: bool
        - missing: list of missing files
        - found: list of found files
    """
    settings = get_settings()
    rules_dir = Path(settings.RULES_DIR)

    if not rules_dir.exists():
        return {
            "valid": False,
            "missing": ["rules/ directory not found"],
            "found": []
        }

    # Required rule files
    required_rules = [
        "common/security.md",
        "common/coding-standards.md",
        "common/git-workflow.md",
        "common/testing.md",
    ]

    missing = []
    found = []

    for rule_path in required_rules:
        rule_file = rules_dir / rule_path
        if rule_file.exists():
            found.append(rule_path)
        else:
            missing.append(rule_path)

    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "found": found
    }
