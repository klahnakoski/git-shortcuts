from mo_future import extend
from mo_threads import Till
from mo_logs import logger
from mo_dots import Data

from mo_git.github.branches import Session


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


@extend(Session)
def wait_for_pr_checks(self, pr_number, please_stop, poll_s=10, required_check_names=None):
    """
    Wait until checks are completed. Returns a result dict including failures.
    Raises on timeout.
    """
    last_seen = None

    while not please_stop:
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

        Till(seconds=poll_s).wait(till=please_stop)
        continue

    raise logger.error("Timed out waiting for checks on PR #{pr_number} (sha {sha})", pr_number=pr_number, sha=sha)
