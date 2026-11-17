"""Checks that need no PowerPoint, so they run on Linux CI as well.

    python3 -m unittest discover -s tests
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "office-render" / "scripts" / "office_render.py"
_spec = importlib.util.spec_from_file_location("office_render", SCRIPT)
office_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(office_render)
ON_MAC_WITH_POWERPOINT = sys.platform == "darwin" and office_render.PP_APP.exists()


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
                   cwd=cwd, check=True, capture_output=True)


class TempDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()


class ProjectRoot(TempDir):
    def test_a_plain_folder_is_its_own_project(self):
        self.assertEqual(office_render.project_root(self.tmp), self.tmp)

    @unittest.skipUnless(office_render.has_git(), "needs git")
    def test_a_subfolder_of_a_repo_maps_to_the_repo(self):
        repo = self.tmp / "repo"
        (repo / "a" / "b").mkdir(parents=True)
        git(repo, "init", "-q")
        self.assertEqual(office_render.project_root(repo / "a" / "b"), repo)

    @unittest.skipUnless(office_render.has_git(), "needs git")
    def test_a_worktree_maps_to_the_main_checkout(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "commit", "-q", "--allow-empty", "-m", "start")
        git(repo, "worktree", "add", "-q", str(self.tmp / "worktree"))
        self.assertEqual(office_render.project_root(self.tmp / "worktree"), repo)

    def test_a_render_dir_is_used_as_given(self):
        self.assertEqual(office_render.render_folder(render_dir=self.tmp / "rd"), (None, self.tmp / "rd"))

    def test_the_render_folder_sits_in_the_project_and_ignores_itself(self):
        root, rd = office_render.render_folder(project=self.tmp)
        self.assertEqual(rd, self.tmp / ".office-render")
        office_render.prepare(rd)
        self.assertIn("*", (rd / ".gitignore").read_text().split())


class Helpers(TempDir):
    def test_owner_pid(self):
        self.assertEqual(office_render.owner_pid("~$office-render-123-1.pptx"), 123)
        self.assertEqual(office_render.owner_pid("~$~$office-render-77-grant.pptx"), 77)
        self.assertEqual(office_render.owner_pid("office-render-55-2.pdf"), 55)
        self.assertIsNone(office_render.owner_pid("~$deck.pptx"))

    def test_pdf_complete(self):
        good, cut = self.tmp / "good.pdf", self.tmp / "cut.pdf"
        good.write_bytes(b"%PDF-1.7\n1 0 obj\n%%EOF\n")
        cut.write_bytes(b"%PDF-1.7\n1 0 obj\n")
        self.assertTrue(office_render.pdf_complete(good))
        self.assertFalse(office_render.pdf_complete(cut))
        self.assertFalse(office_render.pdf_complete(self.tmp / "missing.pdf"))

    def test_tidy_deletes_only_what_dead_renders_left(self):
        dead = self.tmp / "office-render-999999999-1.pdf"        # no process has this pid
        lock = self.tmp / "~$~$office-render-999999999-1.pptx"
        live = self.tmp / f"~$office-render-{os.getpid()}-1.pptx"
        other = self.tmp / "notes.txt"
        for p in (dead, lock, live, other):
            p.write_text("x")
        office_render.tidy(self.tmp)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), sorted([live.name, other.name]))


class Cli(TempDir):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_needs_exactly_one_action(self):
        self.assertEqual(self.cli().returncode, 2)
        self.assertEqual(self.cli("--status", "--grant").returncode, 2)

    def test_status_of_a_new_folder_changes_nothing(self):
        rd = self.tmp / "new"
        r = self.cli("--status", "--render-dir", str(rd))
        self.assertEqual(r.returncode, 3 if ON_MAC_WITH_POWERPOINT else 2, r.stdout + r.stderr)
        self.assertFalse(rd.exists())

    @unittest.skipUnless(ON_MAC_WITH_POWERPOINT, "needs PowerPoint")
    def test_rendering_before_the_grant_stops_with_3(self):
        deck = self.tmp / "deck.pptx"
        deck.write_bytes(office_render.BLANK.read_bytes())
        r = self.cli(str(deck), "--render-dir", str(self.tmp / "rd"))
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("--grant", r.stderr)


if __name__ == "__main__":
    unittest.main()
