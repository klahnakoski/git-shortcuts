import requests
from mo_json_config import get
from mo_http.http import get_json, post_json

config = None


class Session:
    def __init__(self, owner, repo):
        global config
        if not config:
            config = get("file://config.json")
        self.session = None
        self.url = config.github.url
        self.owner = owner
        self.repo = repo

    def __enter__(self):
        s = requests.Session()
        s.headers.update({
            "Authorization": f"Bearer {config.github.token}",
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
        return f"{self.url}/repos/{self.owner}/{self.repo}"

    def get_json(self, path, *, method="GET", **kwargs):
        return get_json(f"{self.repo}{path}", session=self.session, **kwargs)

    def post_json(self, path, **kwargs):
        return post_json(f"{self.repo}{path}", session=self.session, **kwargs)
