import subprocess
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
        self.repo = TempDirectory()
        self.repo.__enter__()
        self.current_dir = Path.cwd()

        # init repo with main branch and identity
        sh(["git", "init", "-b", "main"])
        sh(["git", "config", "user.name", "Test"])
        sh(["git", "config", "user.email", "test@example.com"])

        # seed commit
        (self.repo / "README.md").write("# repo\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "init"])

        # sanity: script exists
        if not HIT.exists():
            self.skipTest(f"hit_merge script not found at {HIT}")

    def tearDown(self):
        Path.chdir(self.current_dir)
        self.repo.__exit__(None, None, None)

    # ---------------------------
    # Tests
    # ---------------------------

    def test_clean_merge_forces_merge_commit_with_fixed_message(self):
        # feature branch
        sh(["git", "checkout", "-b", "feature"])
        (self.repo / "feature.txt").write("hello from feature\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "add feature"])

        # main diverges
        sh(["git", "checkout", "main"])
        (self.repo / "main.txt").write("hello from main\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "add main"])

        # run hit merge (should be clean; our script forces merge commit with message "merge feature")
        merge("feature", expect_rc=0)

        # verify true merge commit (2 parents) and message
        self.assertGreaterEqual(commit_parent_count(self.repo), 2)
        self.assertEqual(git_log_body(self.repo), "merge feature")
        self.assertFalse(in_merge_state(self.repo))

    def test_conflict_writes_theirs_branch_copy_and_exits_nonzero(self):
        # create conflicting changes
        sh(["git", "checkout", "-b", "conflict"])
        (self.repo / "src" / "config.json").write(
            textwrap.dedent("""\
            {"a": 1, "side": "theirs"}
        """),
        )
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "theirs config"])

        sh(["git", "checkout", "main"])
        (self.repo / "src" / "config.json").write(
            textwrap.dedent("""\
            {"a": 1, "side": "ours"}
        """),
        )
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "ours config"])

        # merge -> conflict
        merge("conflict", expect_rc=1)
        self.assertTrue(in_merge_state(self.repo))

        # theirs copy exists as src/config.conflict.json and contains "theirs"
        copy = self.repo / "src" / "config.conflict.json"
        self.assertTrue(copy.exists(), "Expected branch copy not created")
        self.assertIn('"theirs"}', copy.read_text(encoding="utf-8"))

        # cleanup
        sh(["git", "merge", "--abort"])
        self.assertFalse(in_merge_state(self.repo))

    def test_overwrites_branch_copy_on_second_merge(self):
        sh(["git", "checkout", "-b", "feature2"])
        target = self.repo / "app" / "settings.txt"
        target.write("v1 from feature2\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "feat v1"])

        sh(["git", "checkout", "main"])
        target.write("v1 from main\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "main v1"])

        # first merge: conflict -> branch copy with v1 from feature2
        merge("feature2", expect_rc=1)
        copy = self.repo / "app" / "settings.feature2.txt"
        self.assertTrue(copy.exists())
        self.assertEqual(copy.read_text(), "v1 from feature2\n")
        sh(["git", "merge", "--abort"])

        # update both sides to cause conflict again
        sh(["git", "checkout", "feature2"])
        target.write("v2 from feature2\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "feat v2"])

        sh(["git", "checkout", "main"])
        target.write("v2 from main\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "main v2"])

        # second merge: copy should be OVERWRITTEN with v2 content
        merge("feature2", expect_rc=1)
        self.assertTrue(copy.exists())
        self.assertEqual(copy.read_text(), "v2 from feature2\n")
        sh(["git", "merge", "--abort"])

    def test_naming_rules_multi_extension_and_dotfiles(self):
        cases = [
            ("archive.tar.gz", "archive.feature.tar.gz"),
            ("Makefile", "Makefile.feature"),
            (".env", ".env.feature"),
            ("data", "data.feature"),
            ("notes.md", "notes.feature.md"),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                # reset working tree back to main (ensure clean state)
                sh(["git", "checkout", "main"])

                # make conflict for the given filename
                sh(["git", "checkout", "-b", "feature"])
                f = self.repo / name
                f.write("THEIRS\n")
                sh(["git", "add", "-A"])
                sh(["git", "commit", "-m", "theirs"])

                sh(["git", "checkout", "main"])
                f.write("OURS\n")
                sh(["git", "add", "-A"])
                sh(["git", "commit", "-m", "ours"])

                merge("feature", expect_rc=1)
                copy = self.repo / expected
                self.assertTrue(copy.exists(), f"Expected {expected} to exist")
                self.assertEqual(copy.read_text(), "THEIRS\n")
                sh(["git", "merge", "--abort"])

    def test_clean_merge_exit_code_zero_and_not_in_merge_state(self):
        sh(["git", "checkout", "-b", "feat"])
        (self.repo / "x.txt").write("x\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "feat x"])

        sh(["git", "checkout", "main"])
        (self.repo / "y.txt").write("y\n")
        sh(["git", "add", "-A"])
        sh(["git", "commit", "-m", "main y"])

        merge("feat", expect_rc=0)
        self.assertFalse(in_merge_state(self.repo))
        self.assertEqual(git_log_body(self.repo), "merge feat")



# ---------------------------
# Helper functions
# ---------------------------


def sh(args, check=True):
    """Run a shell command in cwd and return CompletedProcess."""
    return subprocess.run(args, check=check, text=True, capture_output=True)


def git_log_body(cwd: Path) -> str:
    out = sh(["git", "log", "-1", "--pretty=%B"], cwd).stdout.strip()
    return out


def commit_parent_count(cwd: Path) -> int:
    # "SHA PARENT1 PARENT2" -> parents count
    parent_out = sh(["git", "rev-list", "--parents", "-n", "1", "HEAD"], cwd).stdout.strip()
    return max(0, len(parent_out.split()) - 1)


def in_merge_state(cwd):
    return bool(File(".git/MERGE_HEAD"))
