import subprocess
from unittest import TestCase, skip

from mo_files import TempDirectory
from mo_json_config import get
from mo_math import randoms
from mo_testing import add_error_reporting
from mo_threads import Till
from mo_logs import logger

from mo_git import github

BRANCH_PREFIX = "test_"

@add_error_reporting
@skip("skipping github session test to avoid hitting rate limits during development")
class TestGithubSession(TestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.config = get("file://tests/config.json").github

    def setUp(self):
        self.repo = TempDirectory()
        self.repo.__enter__()

        # Clone the repo
        token = self.config.token
        owner = self.config.owner
        url = f"https://{token}@github.com/{owner}/mo-git.git"
        self.sh(["git", "clone", url, "."])

    def tearDown(self):
        self.repo.__exit__(None, None, None)

        # Cleanup branches
        with github.Session(repo="mo-git", config=self.config) as session:
            branches = session.list_branches()
            for branch in branches:
                if branch.name.startswith(BRANCH_PREFIX):
                    try:
                        session.delete_branch(branch.name)
                    except Exception as cause:
                        logger.warning("problem", cause=cause)

    def test_create_branch_and_pr(self):
        # Create a unique branch name
        branch_name = f"{BRANCH_PREFIX}{randoms.base64(16)}"

        # Create branch locally off dev, make a change, commit, push
        self.sh(["git", "checkout", "-b", branch_name, "dev"])

        # Make a non-trivial change
        test_file = self.repo / "test_change.txt"
        test_file.write("This is a test change for the PR.\n")
        self.sh(["git", "add", "test_change.txt"])
        self.sh(["git", "commit", "-m", "Add test change for PR"])

        # Push the branch
        self.sh(["git", "push", "origin", branch_name])

        # Open PR
        with github.Session(repo="mo-git", config=self.config) as session:
            pr = session.open_pr(head=branch_name, base="dev", title="Test PR", body="Automated test PR")
            assert pr.number

            # Wait for checks to complete (with timeout)
            # 5 minute timeout
            summary = session.wait_for_pr_checks(pr.number, till=Till(seconds=300), poll_s=10)
            assert summary.all_completed

            # Cleanup: close the PR
            session.close_pr(pr.number)

    def sh(self, args, check=True):
        """Run a shell command in cwd and return CompletedProcess."""

        return subprocess.run(args, cwd=self.repo.os_path, check=check, text=True, capture_output=True)
