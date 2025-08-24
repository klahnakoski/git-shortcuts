import subprocess


def run(cmd, check=True, capture_output=False, text=True):
    result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
    return result.stdout.strip() if capture_output else None
