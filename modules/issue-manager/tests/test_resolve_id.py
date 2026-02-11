"""Tests for short-form issue ID resolution."""

import tempfile
from collections import Counter
from pathlib import Path

import pytest

from amplifier_module_issue_manager import IssueManager


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_dir):
    return IssueManager(temp_dir)


class TestResolveIssueId:
    """Tests for IssueManager.resolve_issue_id()."""

    def test_exact_match_full_uuid(self, manager):
        """Full UUID resolves to itself."""
        issue = manager.create_issue(title="Test")
        assert manager.resolve_issue_id(issue.id) == issue.id

    def test_prefix_match_first_segment(self, manager):
        """First 8 chars (UUID first segment) resolves correctly."""
        issue = manager.create_issue(title="Test")
        prefix = issue.id[:8]
        assert manager.resolve_issue_id(prefix) == issue.id

    def test_prefix_match_short(self, manager):
        """Short prefix resolves if unique."""
        issue = manager.create_issue(title="Test")
        # Use enough chars to be unique with just one issue
        prefix = issue.id[:4]
        assert manager.resolve_issue_id(prefix) == issue.id

    def test_no_match_raises(self, manager):
        """Non-matching prefix raises ValueError."""
        manager.create_issue(title="Test")
        with pytest.raises(ValueError, match="No issue found matching"):
            manager.resolve_issue_id("zzzznotreal")

    def test_no_issues_raises(self, manager):
        """Empty issue list raises ValueError."""
        with pytest.raises(ValueError, match="No issue found matching"):
            manager.resolve_issue_id("anything")

    def test_ambiguous_prefix_raises(self, manager):
        """Ambiguous prefix raises ValueError listing matches."""
        # Create enough issues that a 1-char prefix likely collides
        issues = [manager.create_issue(title=f"Issue {i}") for i in range(20)]

        # Find a prefix shared by at least 2 issues
        first_chars = Counter(i.id[0] for i in issues)
        ambiguous_char = next(c for c, count in first_chars.items() if count > 1)

        with pytest.raises(ValueError, match="Ambiguous issue ID"):
            manager.resolve_issue_id(ambiguous_char)

    def test_resolve_does_not_mutate_index_behavior(self, manager):
        """get_issue() still requires exact match (unchanged)."""
        issue = manager.create_issue(title="Test")
        prefix = issue.id[:8]
        # resolve works with prefix
        assert manager.resolve_issue_id(prefix) == issue.id
        # get_issue still returns None for prefix
        assert manager.get_issue(prefix) is None


class TestResolveInOperations:
    """Integration tests: short IDs work through resolve + operate pattern."""

    def test_get_issue_with_short_id(self, manager):
        """get_issue via resolved prefix returns the issue."""
        issue = manager.create_issue(title="Findable")
        resolved = manager.resolve_issue_id(issue.id[:8])
        found = manager.get_issue(resolved)
        assert found is not None
        assert found.title == "Findable"

    def test_update_issue_with_short_id(self, manager):
        """update_issue works after resolving a prefix."""
        issue = manager.create_issue(title="Original")
        resolved = manager.resolve_issue_id(issue.id[:8])
        updated = manager.update_issue(resolved, title="Updated")
        assert updated.title == "Updated"

    def test_close_issue_with_short_id(self, manager):
        """close_issue works after resolving a prefix."""
        issue = manager.create_issue(title="To close")
        resolved = manager.resolve_issue_id(issue.id[:8])
        closed = manager.close_issue(resolved)
        assert closed.status == "closed"

    def test_add_dependency_with_short_ids(self, manager):
        """add_dependency works after resolving both IDs."""
        issue_a = manager.create_issue(title="Blocked")
        issue_b = manager.create_issue(title="Blocker")
        resolved_a = manager.resolve_issue_id(issue_a.id[:8])
        resolved_b = manager.resolve_issue_id(issue_b.id[:8])
        dep = manager.add_dependency(resolved_a, resolved_b)
        assert dep.from_id == issue_a.id
        assert dep.to_id == issue_b.id
