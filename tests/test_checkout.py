import os
import subprocess
from pathlib import Path
from unittest import TestCase

from mo_files import TempDirectory

from mo_git.checkout import checkout_branch, checkout_new_branch_with_alias


class TestCheckout(TestCase):

    def setUp(self):
        # Fresh temp repo per test
        self.current_dir = Path.cwd()
        self.repo = TempDirectory()
        self.repo.__enter__()
        os.chdir(self.repo.os_path)

        # init repo with main branch and identity
        self.sh(["git", "init", "-b", "main"])
        self.sh(["git", "config", "user.name", "Test"])
        self.sh(["git", "config", "user.email", "test@example.com"])

        # seed commit
        (self.repo / "README.md").write("# repo\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "init"])

    def tearDown(self):
        os.chdir(self.current_dir)
        self.repo.__exit__(None, None, None)

    def test_checkout_preserves_staged_and_unstaged_files(self):
        # Create feature branch with alias
        checkout_new_branch_with_alias("feature-branch", "fb")

        # Add two files: one staged, one unstaged
        staged_file = self.repo / "staged.txt"
        unstaged_file = self.repo / "unstaged.txt"

        staged_file.write("This file should be staged\n")
        unstaged_file.write("This file should be unstaged\n")

        # Stage only the first file
        self.sh(["git", "add", "staged.txt"])

        # Verify initial state
        self.assertTrue(staged_file.exists, "staged.txt should exist")
        self.assertTrue(unstaged_file.exists, "unstaged.txt should exist")
        self.assertTrue(self.is_staged("staged.txt"), "staged.txt should be staged")
        self.assertFalse(self.is_staged("unstaged.txt"), "unstaged.txt should not be staged")

        # Switch back to main
        checkout_branch("main")

        # Verify feature files are gone (stashed)
        self.assertFalse(staged_file.exists, "staged.txt should be stashed (gone)")
        self.assertFalse(unstaged_file.exists, "unstaged.txt should be stashed (gone)")

        # Switch back to feature branch
        checkout_branch("fb")  # Use alias

        # Verify files are back
        self.assertTrue(staged_file.exists, "staged.txt should be restored")
        self.assertTrue(unstaged_file.exists, "unstaged.txt should be restored")

        # Verify staged/unstaged state is preserved
        self.assertTrue(self.is_staged("staged.txt"), "staged.txt should still be staged after restore")
        self.assertFalse(self.is_staged("unstaged.txt"), "unstaged.txt should still be unstaged after restore")

        # Verify content is correct
        self.assertEqual(staged_file.read(), "This file should be staged\n")
        self.assertEqual(unstaged_file.read(), "This file should be unstaged\n")

    def sh(self, args, check=True):
        """Run a shell command in cwd and return CompletedProcess."""
        return subprocess.run(args, cwd=self.repo.os_path, check=check, text=True, capture_output=True)

    def is_staged(self, filepath):
        """Check if a file is staged (in the index)."""
        result = self.sh(["git", "diff", "--cached", "--name-only"])
        staged_files = result.stdout.strip().splitlines()
        return filepath in staged_files

