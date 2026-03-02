import os
import subprocess
import textwrap
from pathlib import Path
from unittest import TestCase

from mo_files import TempDirectory, File

from mo_git.git.merge import merge

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

    def test_partial_merge_conflict_with_clean_hunks(self):
        """
        Test scenario where a single file has multiple change hunks.
        Some hunks merge cleanly (no conflict), others have conflicts.

        Expected behavior (what we want to implement):
        - Clean hunks should be merged automatically
        - Only conflicting hunks use --ours (keep our version)
        - Branch copy contains the feature version for reference on conflicts
        - No conflict markers in final file

        This test verifies:
        1. No merge conflict state after merge completes
        2. Clean hunks are merged (section 1 from feature, section 2 from main)
        3. Conflicting hunks use --ours (section 3 from main)
        4. Feature copy has the feature branch version for comparison
        5. No conflict markers in main file
        """
        # Create initial file with sections
        content_init = textwrap.dedent("""\
            # Header
            
            intro_line_1
            intro_line_2
            intro_line_3
            intro_line_4
            intro_line_5
            intro_line_6
            intro_line_7
            intro_line_8
            
            section_1_line_1
            section_1_line_2
            
            middle_block_1
            middle_block_2
            middle_block_3
            middle_block_4
            middle_block_5
            middle_block_6
            middle_block_7
            middle_block_8
            
            section_2_line_1
            section_2_line_2
            
            spacer_a
            spacer_b
            spacer_c
            spacer_d
            spacer_e
            spacer_f
            spacer_g
            spacer_h
            
            section_3_line_1
            section_3_line_2
            
            outro_1
            outro_2
            outro_3
            outro_4
            outro_5
            outro_6
            outro_7
            outro_8
            
            # Footer
        """)

        # Feature branch: modify sections 1 and 3
        self.sh(["git", "checkout", "main"])
        (self.repo / "multi.txt").write(content_init)
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "init multi.txt"])

        content_feature = textwrap.dedent("""\
            # Header
            
            intro_line_1
            intro_line_2
            intro_line_3
            intro_line_4
            intro_line_5
            intro_line_6
            intro_line_7
            intro_line_8
            
            section_1_line_1_FEATURE
            section_1_line_2_FEATURE
            
            middle_block_1
            middle_block_2
            middle_block_3
            middle_block_4
            middle_block_5
            middle_block_6
            middle_block_7
            middle_block_8
            
            section_2_line_1
            section_2_line_2
            
            spacer_a
            spacer_b
            spacer_c
            spacer_d
            spacer_e
            spacer_f
            spacer_g
            spacer_h
            
            section_3_line_1_FEATURE
            section_3_line_2_FEATURE
            
            outro_1
            outro_2
            outro_3
            outro_4
            outro_5
            outro_6
            outro_7
            outro_8
            
            # Footer
        """)
        self.sh(["git", "checkout", "-b", "feature"])
        (self.repo / "multi.txt").write(content_feature)
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "feature: modify sections 1 and 3"])

        # Main branch: modify sections 2 and 3 (section 3 conflicts with feature)
        self.sh(["git", "checkout", "main"])
        content_main = textwrap.dedent("""\
            # Header
            
            intro_line_1
            intro_line_2
            intro_line_3
            intro_line_4
            intro_line_5
            intro_line_6
            intro_line_7
            intro_line_8
            
            section_1_line_1
            section_1_line_2
            
            middle_block_1
            middle_block_2
            middle_block_3
            middle_block_4
            middle_block_5
            middle_block_6
            middle_block_7
            middle_block_8
            
            section_2_line_1_MAIN
            section_2_line_2_MAIN
            
            spacer_a
            spacer_b
            spacer_c
            spacer_d
            spacer_e
            spacer_f
            spacer_g
            spacer_h
            
            section_3_line_1_MAIN
            section_3_line_2_MAIN
            
            outro_1
            outro_2
            outro_3
            outro_4
            outro_5
            outro_6
            outro_7
            outro_8
            
            # Footer
        """)
        (self.repo / "multi.txt").write(content_main)
        self.sh(["git", "add", "-A"])
        self.sh(["git", "commit", "-m", "main: modify sections 2 and 3"])

        # Merge feature into main
        merge("feature")

        # Verify we're not in merge state (merge completed)
        self.assertFalse(self.in_merge_state(), "Should not be in merge state after completion")

        # Verify feature copy exists with feature's version for reference
        feature_copy = self.repo / "multi.feature.txt"
        self.assertTrue(feature_copy.exists, "Feature copy should exist for conflict reference")
        feature_content = feature_copy.read()
        self.assertIn("section_1_line_1_FEATURE", feature_content,
                      "Feature copy should have feature's section 1")
        self.assertIn("section_3_line_1_FEATURE", feature_content,
                      "Feature copy should have feature's section 3")

        # Verify main file has correct merge result:
        # - Section 1: FEATURE version (clean merge - only feature changed it)
        # - Section 2: MAIN version (clean merge - only main changed it)
        # - Section 3: MAIN version (conflict - we keep ours)
        main_content = (self.repo / "multi.txt").read()

        self.assertIn("section_1_line_1_FEATURE", main_content,
                      "Section 1: should have feature changes (clean merge)")
        self.assertIn("section_2_line_1_MAIN", main_content,
                      "Section 2: should have main changes (clean merge)")
        self.assertIn("section_3_line_1_MAIN", main_content,
                      "Section 3: should have main version (conflict resolved with ours)")

        # Should NOT have conflicting markers in main file
        self.assertNotIn("<<<<<<<", main_content, "No conflict markers should remain")
        self.assertNotIn(">>>>>>>", main_content, "No conflict markers should remain")
        self.assertNotIn("=======", main_content, "No conflict markers should remain")

        # Verify merge commit message
        self.assertEqual(self.git_log_body(), "merge feature")




    # ---------------------------
    # Helper functions
    # ---------------------------

    def sh(self, args, check=True):
        """Run a shell command in cwd and return CompletedProcess."""
        return subprocess.run(args, cwd=self.repo.os_path, check=check, text=True, capture_output=True)


    def git_log_body(self) -> str:
        out = self.sh(["git", "log", "-1", "--pretty=%B"]).stdout.strip()
        return out


    def commit_parent_count(self) -> int:
        # "SHA PARENT1 PARENT2" -> parents count
        parent_out = self.sh(["git", "rev-list", "--parents", "-n", "1", "HEAD"]).stdout.strip()
        return max(0, len(parent_out.split()) - 1)

    def in_merge_state(self):
        return bool(File(".git/MERGE_HEAD"))
