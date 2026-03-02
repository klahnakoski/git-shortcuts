from mo_future import extend

from mo_git.github.utils import Session


@extend(Session)
def create_branch(self, base_branch, new_branch):
    base_sha = self.get_json(f"/git/ref/heads/{base_branch}").object.sha
    payload = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}
    return self.post_json(f"/git/refs", json=payload).object.sha


@extend(Session)
def open_pr(self, head_branch, base_branch, title, body=""):
    payload = {
        "title": title,
        "head": head_branch,  # if cross-fork: "user:branch"
        "base": base_branch,
        "body": body,
        "draft": False,
    }
    return self.post_json("/pulls", json=payload)


@extend(Session)
def create_branch_and_pr(self, base_branch, new_branch, title, body=""):
    self.session.create_branch(base_branch, new_branch)
    pr = self.session.open_pr(new_branch, base_branch, title, body)
    return pr
