"""Intentionally failing synthetic guard, run only in a disposable test repository.

The parent regression demonstrates that weakening this assertion produces a
green check while the fixed-candidate comparison still detects the edit.
"""

import unittest


class SyntheticGuard(unittest.TestCase):
    """Represent a guard whose denied action was incorrectly allowed."""

    def test_denied_action(self):
        """Fail until the adversarial test weakens this assertion."""
        self.assertFalse(True)


if __name__ == "__main__":
    unittest.main()
