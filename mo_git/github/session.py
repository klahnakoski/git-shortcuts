import requests
from mo_kwargs import override
from mo_files import URL
from mo_logs import logger
from mo_threads import Till
from mo_dots import Data, from_data
from mo_git.utils import http_get_json, http_post_json, http_get


class Session:
    @override("config")
    def __init__(self, *, url=None, owner=None, token=None, config=None, repo):
        self.session = None
        self.url = URL(url)
        self.owner = owner
        self.token = token
        self._repo = repo
        self.config = config

    def __enter__(self):
        s = requests.Session()
        s.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agent-actions-bot",
        })
        self.session = s
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.session is not None:
            self.session.close()
        return False

    @property
    def repo(self):
        return self.url / "repos" / self.owner / self._repo

    def get_json(self, path, *, method="GET", **kwargs):
        return http_get_json(self.repo / path, session=self.session, **kwargs)

    def post_json(self, path, json, **kwargs):
        return http_post_json(self.repo / path, session=self.session, json=json, **kwargs)

    def create_branch(self, base_branch, new_branch):
        base_sha = self.get_json(f"/git/ref/heads/{base_branch}").object.sha
        payload = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
        return self.post_json(f"/git/refs", json=payload).object.sha

    def delete_branch(self, branch_name):
        return http_get(self.repo / "git/refs/heads" / branch_name, method="DELETE", session=self.session)

    def list_branches(self):
        return self.get_json("branches")

    @override
    def open_pr(self, *, head, base, title, body="", draft=False, kwargs=None):
        return self.post_json("/pulls", json=from_data(kwargs))

    def close_pr(self, pr_number):
        return http_get_json(
            self.repo / f"pulls/{pr_number}", method="PATCH", session=self.session, json={"state": "closed"}
        )

    def create_branch_and_pr(self, base_branch, new_branch, title, body=""):
        self.session.create_branch(base_branch, new_branch)
        pr = self.session.open_pr(new_branch, base_branch, title, body)
        return pr

    def wait_for_pr_checks(self, pr_number, till, poll_s=10, required_check_names=None):
        """
        Wait until checks are completed. Returns a result dict including failures.
        Raises on timeout.
        """
        last_seen = None

        while not till:
            pr = self.get_json(f"/pulls/{pr_number}")
            sha = pr.head.sha

            check_runs = self.get_json(f"/commits/{sha}/check-runs").check_runs
            summary = summarize_checks(check_runs)

            # Enforce required checks if provided
            if required_check_names:
                missing = [n for n in required_check_names if n not in summary.by_name]
                if missing:
                    summary.all_completed = False
                    summary.all_success = False
                    summary.missing_required = missing

            # Optional: include combined status as fallback signal
            combined = self.get_json(f"/commits/{sha}/status")
            summary.combined_state = combined.state
            summary.sha = sha
            summary.pr_url = pr.html_url

            # Print/debug only when something changes (helps when you wrap into CLI)
            fingerprint = (
                sha,
                tuple(sorted((n, cr.status, cr.conclusion) for n, cr in summary.by_name.items())),
                tuple(summary.missing_required),
                summary.combined_state,
            )
            if fingerprint != last_seen:
                last_seen = fingerprint

            if summary.all_completed:
                return summary

            Till(seconds=poll_s).wait()
            continue

        raise logger.error("Timed out waiting for checks on PR #{pr_number} (sha {sha})", pr_number=pr_number, sha=sha)


def summarize_checks(check_runs):
    """
    Returns:
      {
        "all_completed": bool,
        "all_success": bool,
        "by_name": {name: {...}},
        "failures": [(name, conclusion, details_url, summary)]
      }
    """
    output = Data(all_completed=True, all_success=True,)

    # Multiple check runs can share a name; keep the newest by started_at/updated_at.
    # (Common with reruns.)
    def key_ts(cr):
        return cr.completed_at or cr.started_at or cr.created_at or ""

    for cr in sorted(check_runs, key=key_ts):
        output.by_name[cr.name] = cr

        # None until completed
        if cr.status != "completed":
            output.all_completed = False
            output.all_success = False
            continue

        if cr.conclusion != "success":
            output.all_success = False
            summary = cr.output.summary or cr.output.text
            output.failures.append((cr.name, cr.conclusion, cr.details_url, summary[:500]))

    return output
