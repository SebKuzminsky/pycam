import os
import subprocess


def get_git_describe():
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    proc = subprocess.Popen(["git", "describe", "--tags"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=repo_dir)
    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        return stdout.strip().lstrip(b'v') or None
    else:
        return None


VERSION = get_git_describe()
