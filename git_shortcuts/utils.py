import subprocess

import requests
from mo_json import json2value, scrub


def run(cmd, check=True, capture_output=False, text=True):
    result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
    if capture_output:
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip()
    return None


def http_get(url, *, method="GET", session=None, json=None, **kwargs):
    response = (session or requests).request(method, str(url), json=scrub(json), **kwargs)
    response.raise_for_status()
    return


def http_get_json(url, *, method="GET", session=None, json=None, **kwargs):
    response = (session or requests).request(method, str(url), json=scrub(json), **kwargs)
    response.raise_for_status()
    return json2value(response.text)


def http_post_json(url, **kwargs):
    return http_get_json(url, method="POST", **kwargs)
