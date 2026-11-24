"""Publish the tap's qualified arm64_sequoia bottle and propose its metadata."""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

FORMULA = "Formula/robotweax-srt.rb"
PACKAGE = "robotweax-srt"
BOTTLE_TAG = "arm64_sequoia"
BASE = "main"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(*args, input=None, env=None):
    return subprocess.run(
        args, input=input, env=env, check=True, stdout=subprocess.PIPE
    ).stdout


def api(repo, endpoint, paginate=False, **fields):
    args = ["gh", "api", f"repos/{repo}/{endpoint}"]
    if paginate:
        args.extend(["--paginate", "--slurp"])
    if fields:
        args.extend(["--method", "GET"])
        for key, value in fields.items():
            args.extend(["-f", f"{key}={value}"])
    return json.loads(command(*args))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata_formula(formula, state):
    require(b"\n  bottle do\n" not in formula, "Qualified recipe already has a bottle block")
    anchor = b'  depends_on "cmake" => :build\n'
    require(formula.count(anchor) == 1, "Unexpected formula layout")
    block = (
        f'  bottle do\n'
        f'    root_url "{state["root_url"]}"\n'
        f'    sha256 cellar: :any, {BOTTLE_TAG}: "{state["sha256"]}"\n'
        f'  end\n\n'
    )
    return formula.replace(anchor, block.encode() + anchor)


def qualified_bottle(repo, state, pr, formula):
    run_id = state["qualification_run"]
    run = api(repo, f"actions/runs/{run_id}")
    require(
        run["head_sha"] == state["head"]
        and run["head_branch"] == pr["head"]["ref"]
        and run["head_repository"]["id"] == pr["head"]["repo"]["id"]
        and run["event"] == "pull_request"
        and run["path"] == ".github/workflows/tests.yml"
        and run["conclusion"] == "success",
        "The selected run did not qualify this pull request head",
    )
    attempt = run["run_attempt"]
    jobs = api(repo, f"actions/runs/{run_id}/attempts/{attempt}/jobs")["jobs"]
    step_name = f'Qualify {state["version"]} bottle consumers and upgrade'
    require(
        any(
            job["name"] == "test-bot (macos-15)"
            and job["conclusion"] == "success"
            and any(step["name"] == step_name and step["conclusion"] == "success" for step in job["steps"])
            for job in jobs
        ),
        "Native macOS bottle and upgrade qualification did not pass",
    )
    pages = api(repo, f"actions/runs/{run_id}/artifacts", paginate=True)
    artifacts = [
        artifact
        for page in pages
        for artifact in page["artifacts"]
        if artifact["name"] == "bottles_macos-15" and not artifact["expired"]
    ]
    require(len(artifacts) == 1, "Expected one retained macOS bottle artifact")
    artifact = artifacts[0]
    data = command("gh", "api", f'repos/{repo}/actions/artifacts/{artifact["id"]}/zip')
    require(artifact["digest"] == f"sha256:{digest(data)}", "Qualification artifact digest mismatch")
    return checked_bottle(data, repo, state, formula)


def checked_bottle(data, repo, state, formula):
    local_name = state["filename"].replace(f"{PACKAGE}-", f"{PACKAGE}--", 1)
    metadata_name = local_name.removesuffix(".tar.gz") + ".json"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(sorted(archive.namelist()) == sorted([local_name, metadata_name]), "Unexpected bottle artifact files")
        bottle = archive.read(local_name)
        metadata = json.loads(archive.read(metadata_name))
    qualified = metadata[f'{repo.split("/")[0].lower()}/tap/{PACKAGE}']
    spec = qualified["bottle"]
    tag = spec["tags"][BOTTLE_TAG]
    require(
        qualified["formula"]["pkg_version"] == state["version"]
        and qualified["formula"]["tap_git_path"] == FORMULA
        and spec["root_url"] == state["root_url"]
        and spec["cellar"] == "any"
        and spec["rebuild"] == 0
        and set(spec["tags"]) == {BOTTLE_TAG}
        and tag["filename"] == state["filename"]
        and tag["local_filename"] == local_name
        and tag["tab"]["arch"] == "arm64"
        and tag["tab"]["built_on"]["os_version"].startswith("macOS 15.")
        and tag["sha256"] == digest(bottle),
        "Bottle bytes or metadata differ from the qualified release",
    )
    verify_embedded_formula(bottle, state, formula)
    return bottle


def verify_embedded_formula(bottle, state, formula):
    with tarfile.open(fileobj=io.BytesIO(bottle), mode="r:gz") as archive:
        embedded = archive.extractfile(f'{PACKAGE}/{state["version"]}/.brew/{PACKAGE}.rb')
        require(embedded is not None and embedded.read() == formula, "Bottle recipe does not match the PR head")


def receipt(state):
    return (
        f'Publish {PACKAGE} {state["version"]} bottle\n\n'
        f'Qualification-Run: {state["qualification_run"]}\n'
        f'Bottle-SHA256: {state["sha256"]}\n'
    )


def metadata_branch(state, formula, existing):
    branch = state["branch"]
    if existing:
        message = command("git", "show", "-s", "--format=%B", existing).decode()
        match = re.search(r"^Bottle-SHA256: ([0-9a-f]{64})$", message, re.M)
        require(match is not None, "Existing metadata branch has no bottle digest")
        state["sha256"] = match[1]
        parents = command("git", "show", "-s", "--format=%P", existing).decode().strip()
        paths = command("git", "diff", "--name-only", state["head"], existing).decode().splitlines()
        require(
            parents == state["head"]
            and paths == [FORMULA]
            and message.strip() == receipt(state).strip()
            and command("git", "show", f"{existing}:{FORMULA}") == metadata_formula(formula, state),
            "Existing metadata branch differs from the selected qualification",
        )
        return existing

    # Use a private index so the workflow continues executing its main-branch code.
    with tempfile.TemporaryDirectory() as directory:
        env = {
            **os.environ,
            "GIT_INDEX_FILE": str(Path(directory) / "index"),
            "GIT_AUTHOR_NAME": "github-actions[bot]",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "github-actions[bot]",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        }
        command("git", "read-tree", state["head"], env=env)
        blob = command("git", "hash-object", "-w", "--stdin", input=metadata_formula(formula, state))
        command("git", "update-index", "--cacheinfo", f"100644,{blob.decode().strip()},{FORMULA}", env=env)
        tree = command("git", "write-tree", env=env).decode().strip()
        commit = command("git", "commit-tree", tree, "-p", state["head"], input=receipt(state).encode(), env=env)
    sha = commit.decode().strip()
    command("git", "push", "origin", f"{sha}:refs/heads/{branch}")
    return sha


def release_for(repo, state):
    pages = api(repo, "releases", paginate=True)
    matches = [release for page in pages for release in page if release["tag_name"] == state["tag"]]
    require(len(matches) <= 1, "Multiple releases exist for this bottle tag")
    return matches[0] if matches else None


def release_asset(release, state):
    if release is None:
        return None
    require(not release["prerelease"], "Existing bottle release is a prerelease")
    matches = [asset for asset in release["assets"] if asset["name"] == state["filename"]]
    require(len(matches) <= 1, "Multiple assets exist for this bottle")
    if matches:
        require(matches[0]["state"] == "uploaded", "Existing bottle upload is incomplete")
        return matches[0]
    return None


def download_asset(repo, asset):
    return command(
        "gh", "api", "-H", "Accept: application/octet-stream",
        f'repos/{repo}/releases/assets/{asset["id"]}',
    )


def verify_attestation(repo, path):
    result = subprocess.run(
        ["gh", "attestation", "verify", str(path), "--repo", repo,
         "--signer-workflow", f"{repo}/.github/workflows/publish.yml",
         "--source-ref", f"refs/heads/{BASE}", "--deny-self-hosted-runners"],
        stdout=subprocess.DEVNULL,
    )
    return result.returncode == 0


def metadata_pr(repo, branch):
    owner = repo.split("/")[0]
    prs = api(repo, "pulls", state="all", head=f"{owner}:{branch}", base=BASE)
    require(len(prs) <= 1, "Multiple metadata PRs exist")
    if not prs:
        return None
    pr = prs[0]
    require(pr["state"] == "open" or pr.get("merged_at"), f'Metadata PR is closed: {pr["html_url"]}')
    return pr


def prepare(repo, work):
    pr_number, head, run_id = (os.environ[key] for key in ("RELEASE_PR", "QUALIFIED_HEAD", "QUALIFICATION_RUN"))
    require(re.fullmatch(r"[1-9][0-9]*", pr_number) and re.fullmatch(r"[1-9][0-9]*", run_id),
            "PR and qualification run must be numeric IDs")
    require(re.fullmatch(r"[0-9a-f]{40}", head), "Use the full qualified commit SHA")
    pr = api(repo, f"pulls/{pr_number}")
    require(
        pr["base"]["ref"] == BASE and pr["head"]["repo"]["full_name"] == repo
        and pr["head"]["sha"] == head,
        "The release PR must target main in this tap at the qualified head",
    )
    command("git", "fetch", "--no-tags", "origin", f"refs/pull/{pr_number}/head")
    require(command("git", "rev-parse", "FETCH_HEAD").decode().strip() == head, "Release PR head changed")
    formula = command("git", "show", f"{head}:{FORMULA}")
    versions = re.findall(rb'^  version "([0-9]+\.[0-9]+\.[0-9]+)"$', formula, re.M)
    require(len(versions) == 1, "Expected an explicit stable formula version")
    version = versions[0].decode()
    tag = f"{PACKAGE}-{version}"
    branch = f"bottle-publication/pr-{pr_number}-{head}"
    state = dict(
        pr=pr_number, head=head, qualification_run=run_id, version=version, branch=branch, tag=tag,
        filename=f"{tag}.{BOTTLE_TAG}.bottle.tar.gz",
        root_url=f"https://github.com/{repo}/releases/download/{tag}",
    )
    pending_pr = metadata_pr(repo, branch)
    ref = f"refs/heads/{branch}"
    existing = command("git", "ls-remote", "origin", ref).decode().split()
    if pending_pr:
        # GitHub retains the PR head ref after deleting a merged branch.
        ref = f'refs/pull/{pending_pr["number"]}/head'
    else:
        require(os.environ["PR_TOKEN_CONFIGURED"] == "true", "Configure BOTTLE_PUBLICATION_PR_TOKEN")
    if existing or pending_pr:
        command("git", "fetch", "--no-tags", "origin", ref)
        commit = command("git", "rev-parse", "FETCH_HEAD").decode().strip()
        state["metadata_head"] = metadata_branch(state, formula, commit)
    else:
        require(pr["state"] == "open" and not pr["draft"], "The release PR must be ready for review")
    release = release_for(repo, state)
    asset = release_asset(release, state)
    if asset and "metadata_head" in state:
        bottle = download_asset(repo, asset)
    else:
        bottle = qualified_bottle(repo, state, pr, formula)
        if asset:
            require(download_asset(repo, asset) == bottle, "The release already contains different bottle bytes")
    checksum = digest(bottle)
    require(state.get("sha256", checksum) == checksum, "Bottle SHA-256 differs from publication metadata")
    if asset and "metadata_head" in state:
        verify_embedded_formula(bottle, state, formula)
    state["sha256"] = checksum
    path = work / state["filename"]
    path.write_bytes(bottle)
    attested = verify_attestation(repo, path)
    require(not asset or attested, "The existing release asset has no verified publication provenance")
    if "metadata_head" not in state:
        state["metadata_head"] = metadata_branch(state, formula, None)
    (work / "state.json").write_text(json.dumps(state))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"path={path}\nattested={str(attested).lower()}\n")


def publish(repo, state, work):
    path = work / state["filename"]
    require(digest(path.read_bytes()) == state["sha256"], "Bottle changed after preparation")
    release = release_for(repo, state)
    if release is None:
        command(
            "gh", "release", "create", state["tag"], "-R", repo, "--draft",
            "--target", os.environ["GITHUB_SHA"], "--title", state["tag"],
            "--notes", f'Bottle qualified in {repo} pull request #{state["pr"]}.',
        )
        release = release_for(repo, state)
        require(release is not None, "Created release is unavailable")
    asset = release_asset(release, state)
    if asset is None:
        command("gh", "release", "upload", state["tag"], str(path), "-R", repo)
        release = release_for(repo, state)
        asset = release_asset(release, state)
    require(asset and digest(download_asset(repo, asset)) == state["sha256"], "Published asset SHA-256 mismatch")
    if release["draft"]:
        command("gh", "release", "edit", state["tag"], "-R", repo, "--draft=false")
        require(not release_for(repo, state)["draft"], "Bottle release is still a draft")
    print(f'Published verified bottle: {state["root_url"]}/{state["filename"]}')


def open_pr(repo, state):
    pr = metadata_pr(repo, state["branch"])
    if pr:
        require(pr["head"]["sha"] == state["metadata_head"], "Metadata PR head changed after verification")
        url = pr["html_url"]
        status = "Merged" if pr.get("merged_at") else "Pending merge"
    else:
        remote = command("git", "ls-remote", "origin", f'refs/heads/{state["branch"]}').decode().split()
        require(remote and remote[0] == state["metadata_head"], "Metadata branch changed after verification")
        body = (
            f'Publishes the verified {state["filename"]} bottle from #{state["pr"]}.\n\n'
            f'Qualified head: `{state["head"]}`\n'
            f'SHA-256: `{state["sha256"]}`\n\n'
            f'[Native qualification](https://github.com/{repo}/actions/runs/{state["qualification_run"]})\n\n'
            f'[Published bottle]({state["root_url"]}/{state["filename"]})'
        )
        env = {**os.environ, "GH_TOKEN": os.environ["BOTTLE_PUBLICATION_PR_TOKEN"]}
        pr = json.loads(command(
            "gh", "api", "--method", "POST", f"repos/{repo}/pulls",
            "-f", f"base={BASE}", "-f", f'head={state["branch"]}',
            "-f", f'title=Publish {PACKAGE} {state["version"]} bottle metadata', "-f", f"body={body}",
            env=env,
        ))
        require(pr["head"]["sha"] == state["metadata_head"], "Created metadata PR has an unexpected head")
        url = pr["html_url"]
        status = "Pending merge"
    print(f"{status}: {url}")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write(f"{status}: [Bottle metadata PR]({url})\n")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    work = Path(os.environ["RUNNER_TEMP"]) / "bottle-publication"
    work.mkdir(exist_ok=True)
    operation = sys.argv[1]
    if operation == "prepare":
        prepare(repo, work)
        return
    state = json.loads((work / "state.json").read_text())
    if operation == "publish":
        publish(repo, state, work)
    elif operation == "open-pr":
        open_pr(repo, state)
    else:
        raise ValueError(f"Unknown publication operation: {operation}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
