import importlib.util
import io
import json
import os
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "publish_bottle", Path(__file__).parents[1] / "scripts/publish-bottle.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

REPO = "Robotweax/homebrew-tap"
HEAD = "1" * 40
METADATA_HEAD = "2" * 40
FORMULA = b'class RobotweaxSrt < Formula\n  version "0.3.5"\n\n  depends_on "cmake" => :build\nend\n'
FILENAME = "robotweax-srt-0.3.5.arm64_sequoia.bottle.tar.gz"
LOCAL_BOTTLE = FILENAME.replace("srt-", "srt--", 1)
ROOT_URL = f"https://github.com/{REPO}/releases/download/robotweax-srt-0.3.5"


def make_artifact(embedded=FORMULA, tag_digest=None):
    compressed = io.BytesIO()
    with tarfile.open(fileobj=compressed, mode="w:gz") as tar:
        recipe = tarfile.TarInfo("robotweax-srt/0.3.5/.brew/robotweax-srt.rb")
        recipe.size = len(embedded)
        tar.addfile(recipe, io.BytesIO(embedded))
    bottle = compressed.getvalue()
    tag = {
        "filename": FILENAME, "local_filename": LOCAL_BOTTLE,
        "sha256": tag_digest or publisher.digest(bottle),
        "tab": {"arch": "arm64", "built_on": {"os_version": "macOS 15.8"}},
    }
    metadata = {"robotweax/tap/robotweax-srt": {
        "formula": {"pkg_version": "0.3.5", "tap_git_path": publisher.FORMULA},
        "bottle": {"root_url": ROOT_URL, "cellar": "any", "rebuild": 0,
                   "tags": {"arm64_sequoia": tag}},
    }}
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as zip_file:
        zip_file.writestr(LOCAL_BOTTLE, bottle)
        zip_file.writestr(LOCAL_BOTTLE.removesuffix(".tar.gz") + ".json", json.dumps(metadata))
    return data.getvalue(), bottle


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.state = dict(
            pr="16", version="0.3.5", head=HEAD, filename=FILENAME, root_url=ROOT_URL,
            qualification_run="100", branch=f"bottle-publication/pr-16-{HEAD}",
            tag="robotweax-srt-0.3.5", sha256=publisher.digest(b"verified bytes"),
            metadata_head=METADATA_HEAD,
        )
        self.asset = {"name": FILENAME, "id": 9, "state": "uploaded"}
        self.release = {"draft": False, "prerelease": False, "assets": [self.asset]}
        self.source_pr = {
            "state": "open", "draft": False, "base": {"ref": "main"},
            "head": {"sha": HEAD, "ref": "dev/release", "repo": {"full_name": REPO, "id": 77}},
        }
        self.environment = {
            "RELEASE_PR": "16", "QUALIFIED_HEAD": HEAD, "QUALIFICATION_RUN": "100",
            "PR_TOKEN_CONFIGURED": "true", "GITHUB_OUTPUT": str(self.work / "output"),
            "GITHUB_STEP_SUMMARY": str(self.work / "summary"),
        }

    def test_validates_bottle_metadata_and_embedded_recipe(self):
        archive, bottle = make_artifact()
        self.assertEqual(publisher.checked_bottle(archive, REPO, self.state, FORMULA), bottle)
        wrong_recipe, _ = make_artifact(embedded=b"other formula")
        with self.assertRaisesRegex(ValueError, "recipe does not match"):
            publisher.checked_bottle(wrong_recipe, REPO, self.state, FORMULA)
        wrong_digest, _ = make_artifact(tag_digest="0" * 64)
        with self.assertRaisesRegex(ValueError, "bytes or metadata differ"):
            publisher.checked_bottle(wrong_digest, REPO, self.state, FORMULA)

    @patch.object(publisher, "api")
    def test_requires_the_exact_successfully_qualified_head(self, api):
        run = {
            "head_sha": "3" * 40, "head_branch": "dev/release", "head_repository": {"id": 77},
            "event": "pull_request", "path": ".github/workflows/tests.yml",
            "conclusion": "success", "run_attempt": 1,
        }
        api.return_value = run
        with self.assertRaisesRegex(ValueError, "did not qualify"):
            publisher.qualified_bottle(REPO, self.state, self.source_pr, FORMULA)
        run["head_sha"] = HEAD
        api.side_effect = [run, {"jobs": [{"name": "test-bot (macos-15)", "conclusion": "success",
                                          "steps": [{"name": "Qualify 0.3.5 bottle consumers and upgrade",
                                                     "conclusion": "skipped"}]}]}]
        with self.assertRaisesRegex(ValueError, "qualification did not pass"):
            publisher.qualified_bottle(REPO, self.state, self.source_pr, FORMULA)

    def retry(self, attested, data, merged=False):
        pr = {"number": 17, "merged_at": "2026-11-24"} if merged else None

        def git(*args):
            if args[1] == "rev-parse":
                head = HEAD if git.last_ref == "refs/pull/16/head" else METADATA_HEAD
                return head.encode()
            if args[1] == "show":
                return FORMULA
            if args[1] == "fetch":
                git.last_ref = args[-1]
            if args[1] == "ls-remote" and not merged:
                return METADATA_HEAD.encode()
            return b""

        def inspect(state, formula, existing):
            self.assertEqual(existing, METADATA_HEAD)
            state["sha256"] = self.state["sha256"]
            return existing

        with (
            patch.dict(os.environ, self.environment),
            patch.object(publisher, "command", side_effect=git),
            patch.object(publisher, "api", return_value=self.source_pr),
            patch.object(publisher, "metadata_pr", return_value=pr),
            patch.object(publisher, "metadata_branch", side_effect=inspect),
            patch.object(publisher, "release_for", return_value=self.release),
            patch.object(publisher, "download_asset", return_value=data),
            patch.object(publisher, "verify_embedded_formula"),
            patch.object(publisher, "verify_attestation", return_value=attested),
            patch.object(publisher, "qualified_bottle") as qualification,
        ):
            publisher.prepare(REPO, self.work)
            qualification.assert_not_called()
        self.assertIn("attested=true", (self.work / "output").read_text())
        self.assertEqual((self.work / FILENAME).read_bytes(), b"verified bytes")

    def test_retry_reuses_verified_bytes_without_a_retained_artifact(self):
        self.retry(attested=True, data=b"verified bytes")

    def test_retry_reuses_the_merged_pr_when_its_branch_was_deleted(self):
        self.retry(attested=True, data=b"verified bytes", merged=True)

    def test_retry_rejects_different_bytes_or_missing_provenance(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
            self.retry(attested=True, data=b"other bytes")
        with self.assertRaisesRegex(ValueError, "no verified publication provenance"):
            self.retry(attested=False, data=b"verified bytes")

    @patch.object(publisher, "command")
    @patch.object(publisher, "release_for")
    @patch.object(publisher, "download_asset", return_value=b"verified bytes")
    def test_publish_reuses_existing_release_and_asset(self, download, release, command):
        (self.work / FILENAME).write_bytes(b"verified bytes")
        release.return_value = self.release
        publisher.publish(REPO, self.state, self.work)
        download.assert_called_once_with(REPO, self.asset)
        command.assert_not_called()

    @patch.object(publisher, "command")
    @patch.object(publisher, "metadata_pr")
    def test_open_pr_reuses_pending_pr_and_rejects_head_change(self, metadata_pr, command):
        metadata_pr.return_value = {
            "state": "open", "html_url": "https://github.com/Robotweax/homebrew-tap/pull/17",
            "head": {"sha": METADATA_HEAD},
        }
        with patch.dict(os.environ, self.environment):
            publisher.open_pr(REPO, self.state)
            metadata_pr.return_value["head"]["sha"] = "3" * 40
            with self.assertRaisesRegex(ValueError, "head changed"):
                publisher.open_pr(REPO, self.state)
        self.assertIn("Pending merge", (self.work / "summary").read_text())
        command.assert_not_called()

    @patch.object(publisher, "release_for")
    @patch.object(publisher, "download_asset", return_value=b"verified bytes")
    @patch.object(publisher, "command")
    def test_publish_can_resume_a_draft_after_asset_upload(self, command, download, release):
        (self.work / FILENAME).write_bytes(b"verified bytes")
        draft = {**self.release, "draft": True}
        release.side_effect = [draft, self.release]
        publisher.publish(REPO, self.state, self.work)
        command.assert_called_once_with(
            "gh", "release", "edit", self.state["tag"], "-R", REPO, "--draft=false"
        )
        download.assert_called_once_with(REPO, self.asset)

    @patch.object(publisher, "metadata_pr", return_value=None)
    @patch.object(publisher, "command")
    def test_opens_a_pr_for_the_verified_branch_using_only_the_pr_credential(self, command, lookup):
        new_pr = {"head": {"sha": METADATA_HEAD}, "html_url": "https://github.com/example/pull/9"}
        command.side_effect = [METADATA_HEAD.encode(), json.dumps(new_pr).encode()]
        with patch.dict(os.environ, {**self.environment, "BOTTLE_PUBLICATION_PR_TOKEN": "test-token"}):
            publisher.open_pr(REPO, self.state)
        lookup.assert_called_once_with(REPO, self.state["branch"])
        self.assertEqual(command.call_args.args[:5], ("gh", "api", "--method", "POST", f"repos/{REPO}/pulls"))
        self.assertIn(f'head={self.state["branch"]}', command.call_args.args)
        self.assertEqual(command.call_args.kwargs["env"]["GH_TOKEN"], "test-token")
        self.assertIn("Pending merge", (self.work / "summary").read_text())
