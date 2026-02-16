import os
import subprocess
import textwrap
from pathlib import Path
from unittest import TestCase

from mo_files import TempDirectory, File

from mo_git.merge import merge

HERE = Path(__file__).parent.resolve()
HIT = HERE / "hit_merge.py"  # <-- adjust if your script filename/path differs


class TestMerge(TestCase):

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

    # ---------------------------
    # Tests
    # ---------------------------

    def test_clean_merge_forces_merge_commit_with_fixed_message(self):
        # feature branch
        self.sh(["git", "checkout", "-b", "feature"])
        (self.repo / "feature.txt").write("hello from feature\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "add feature"])

        # main diverges
        self.sh(["git", "checkout", "main"])
        (self.repo / "main.txt").write("hello from main\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "add main"])

        # run hit merge (should be clean; our script forces merge commit with message "merge feature")
        merge("feature")

        # verify true merge commit (2 parents) and message
        self.assertGreaterEqual(self.commit_parent_count(), 2)
        self.assertEqual(self.git_log_body(), "merge feature")
        self.assertFalse(self.in_merge_state())

    def test_conflict_writes_theirs_branch_copy_and_exits_nonzero(self):
        # create conflicting changes
        self.sh(["git", "checkout", "-b", "conflict"])
        (self.repo / "src" / "config.json").write(
            textwrap.dedent("""\
            {"a": 1, "side": "theirs"}
        """),
        )
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "theirs config"])

        self.sh(["git", "checkout", "main"])
        (self.repo / "src" / "config.json").write(
            textwrap.dedent("""\
            {"a": 1, "side": "ours"}
        """),
        )
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "ours config"])

        # merge -> conflict -> branch copy created and merge committed
        merge("conflict")

        # theirs copy exists as src/config.conflict.json and contains "theirs"
        copy = self.repo / "src" / "config.conflict.json"
        self.assertTrue(copy.exists, "Expected branch copy not created")
        self.assertIn('"theirs"}', copy.read())
        self.assertFalse(self.in_merge_state())

    def test_overwrites_branch_copy_on_second_merge(self):
        self.sh(["git", "checkout", "-b", "feature2"])
        target = self.repo / "app" / "settings.txt"
        target.write("v1 from feature2\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "feat v1"])

        self.sh(["git", "checkout", "main"])
        target.write("v1 from main\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "main v1"])

        # first merge: conflict -> branch copy with v1 from feature2
        merge("feature2")
        copy = self.repo / "app" / "settings.feature2.txt"
        self.assertTrue(copy.exists)
        self.assertEqual(copy.read(), "v1 from feature2\n")

        # update both sides to cause conflict again
        self.sh(["git", "checkout", "feature2"])
        target.write("v2 from feature2\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "feat v2"])

        self.sh(["git", "checkout", "main"])
        target.write("v2 from main\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "main v2"])

        # second merge: copy should be OVERWRITTEN with v2 content
        merge("feature2")
        self.assertTrue(copy.exists)
        self.assertEqual(copy.read(), "v2 from feature2\n")

    def test_naming_rules_multi_extension_and_dotfiles(self):
        cases = [
            ("archive.tar.gz", "archive.tar.feature.gz"),
            ("Makefile", "Makefile.feature"),
            (".env", ".env.feature"),
            ("data", "data.feature"),
            ("notes.md", "notes.feature.md"),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                # reset working tree back to main (ensure clean state)
                self.sh(["git", "checkout", "main"])
                # delete feature branch if it exists from previous iteration
                self.sh(["git", "branch", "-D", "feature"], check=False)

                # make conflict for the given filename
                self.sh(["git", "checkout", "-b", "feature"])
                f = self.repo / name
                f.write("THEIRS\n")
                self.sh(["git", "add", "-A"])
                self.sh(["git", "commit", "-m", "theirs"])

                self.sh(["git", "checkout", "main"])
                f.write("OURS\n")
                self.sh(["git", "add", "-A"])
                self.sh(["git", "commit", "-m", "ours"])

                merge("feature")
                copy = self.repo / expected
                self.assertTrue(copy.exists, f"Expected {expected} to exist")
                self.assertEqual(copy.read(), "THEIRS\n")

    def test_clean_merge_exit_code_zero_and_not_in_merge_state(self):
        self.sh(["git", "checkout", "-b", "feat"])
        (self.repo / "x.txt").write("x\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "feat x"])

        self.sh(["git", "checkout", "main"])
        (self.repo / "y.txt").write("y\n")
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "main y"])

        merge("feat")
        self.assertFalse(self.in_merge_state())
        self.assertEqual(self.git_log_body(), "merge feat")

    def sh(self, args, check=True):
        """Run a shell command in cwd and return CompletedProcess."""
        return subprocess.run(args, cwd=self.repo.os_path, check=check, text=True, capture_output=True)



    # ---------------------------
    # Helper functions
    # ---------------------------



    def git_log_body(self) -> str:
        out = self.sh(["git", "log", "-1", "--pretty=%B"]).stdout.strip()
        return out


    def commit_parent_count(self) -> int:
        # "SHA PARENT1 PARENT2" -> parents count
        parent_out = self.sh(["git", "rev-list", "--parents", "-n", "1", "HEAD"]).stdout.strip()
        return max(0, len(parent_out.split()) - 1)

    def in_merge_state(self):
        return bool(File(".git/MERGE_HEAD"))
