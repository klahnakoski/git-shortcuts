import os
import subprocess
from pathlib import Path
from unittest import TestCase

from mo_files import TempDirectory

from git_shortcuts.git.checkout import checkout_branch, checkout_new_branch_with_alias


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

    def test_checkout_nonexistent_branch_does_nothing(self):
        # Get current branch
        current_branch = self.sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        self.assertEqual(current_branch, "main")

        # Create a file and stage it
        test_file = self.repo / "test.txt"
        test_file.write("original content\n")
        self.sh(["git", "add", "test.txt"])

        # Verify it's staged
        self.assertTrue(self.is_staged("test.txt"), "test.txt should be staged")

        # Try to checkout non-existent branch
        checkout_branch("does-not-exist")

        # Verify we're still on main branch
        still_on_branch = self.sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        self.assertEqual(still_on_branch, "main", "Should still be on main branch")

        # Verify file still exists and is still staged
        self.assertTrue(test_file.exists, "test.txt should still exist")
        self.assertTrue(self.is_staged("test.txt"), "test.txt should still be staged")
        self.assertEqual(test_file.read(), "original content\n", "Content should be unchanged")

    def test_checkout_new_branch_with_alias_and_base(self):
        # Create a master branch
        self.sh(["git", "checkout", "-b", "master"])
        self.sh(["git", "checkout", "main"])  # back to main

        # Use subprocess to call the CLI for creating new branch with alias and from base
        result = subprocess.run([
            "gscut", "checkout", "-b", "this-is-a-test", "--as", "test", "--from", "master"
        ], cwd=self.repo.os_path, capture_output=True, text=True)

        # Should succeed
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")

        # Check that we are on the new branch
        current_branch = self.sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        self.assertEqual(current_branch, "this-is-a-test")

        # Check that the alias was created
        alias_file = self.repo / ".git" / "gscut-aliases.json"
        self.assertTrue(alias_file.exists, "Alias file should exist")
        import json
        aliases = json.loads(alias_file.read())
        self.assertIn("test", aliases, "Alias 'test' should be in aliases")
        self.assertEqual(aliases["test"], "this-is-a-test", "Alias 'test' should map to 'this-is-a-test'")

    def sh(self, args, check=True):
        """Run a shell command in cwd and return CompletedProcess."""
        return subprocess.run(args, cwd=self.repo.os_path, check=check, text=True, capture_output=True)

    def is_staged(self, filepath):
        """Check if a file is staged (in the index)."""
        result = self.sh(["git", "diff", "--cached", "--name-only"])
        staged_files = result.stdout.strip().splitlines()
        return filepath in staged_files

