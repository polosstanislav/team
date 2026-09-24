#!/usr/bin/env python3
"""Tests for board.py. Run: python3 test_board.py"""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import board  # noqa: E402


def run(board_dir, *argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = board.main(["--board", str(board_dir), *argv])
    return code, out.getvalue().strip(), err.getvalue().strip()


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.board = self.root / ".board"
        self.assertEqual(run(self.board, "init", "--key", "TEAM")[0], 0)

    def tearDown(self):
        self.tmp.cleanup()

    def body_file(self, text):
        path = self.root / "body.md"
        path.write_text(text)
        return str(path)

    def test_init_creates_status_folders_counter_and_project(self):
        folders = sorted(p.name for p in self.board.iterdir() if p.is_dir())
        self.assertEqual(folders, ["1-backlog", "2-todo", "3-development", "4-code-review", "5-testing", "6-done"])
        self.assertEqual((self.board / "counter").read_text().strip(), "1")
        self.assertTrue((self.board / "PROJECT.md").exists())

    def test_init_twice_fails(self):
        code, _, err = run(self.board, "init", "--key", "TEAM")
        self.assertEqual(code, 1)
        self.assertIn("already initialised", err)

    def test_new_allocates_sequential_ids_into_todo(self):
        _, first, _ = run(self.board, "new", "--title", "Cache parsed results", "--owner", "parser-engineer")
        _, second, _ = run(self.board, "new", "--title", "Add login page!", "--owner", "human", "--status", "backlog")
        self.assertTrue(first.endswith("2-todo/TEAM-1-cache-parsed-results.md"))
        self.assertTrue(second.endswith("1-backlog/TEAM-2-add-login-page.md"))
        meta, body, comments = board.parse_ticket(Path(first).read_text())
        self.assertEqual((meta["id"], meta["owner"], meta["blocked_by"]), ("TEAM-1", "parser-engineer", []))
        self.assertIn("Done when", body)
        self.assertEqual(comments, "## Comments")  # empty section, no entries yet

    def test_list_filters_by_status(self):
        run(self.board, "new", "--title", "A", "--owner", "human")
        run(self.board, "new", "--title", "B", "--owner", "human", "--status", "done")
        self.assertEqual(run(self.board, "list")[1].splitlines(), ["TEAM-1\ttodo\tA", "TEAM-2\tdone\tB"])
        self.assertEqual(run(self.board, "list", "--status", "done")[1], "TEAM-2\tdone\tB")

    def test_move_changes_folder_and_rejects_unknown_status(self):
        run(self.board, "new", "--title", "A", "--owner", "human")
        code, out, _ = run(self.board, "move", "TEAM-1", "development")
        self.assertEqual((code, out), (0, "TEAM-1: todo -> development"))
        self.assertTrue(run(self.board, "path", "TEAM-1")[1].endswith("3-development/TEAM-1-a.md"))
        self.assertEqual(run(self.board, "move", "TEAM-1", "review")[0], 1)
        self.assertEqual(run(self.board, "move", "TEAM-1", "development")[0], 1)

    def test_id_prefix_does_not_match_longer_ids(self):
        for title in [str(n) for n in range(1, 13)]:
            run(self.board, "new", "--title", title, "--owner", "human")
        self.assertTrue(run(self.board, "path", "TEAM-1")[1].endswith("TEAM-1-1.md"))
        self.assertTrue(run(self.board, "path", "TEAM-12")[1].endswith("TEAM-12-12.md"))

    def test_comments_append_and_survive_describe(self):
        run(self.board, "new", "--title", "A", "--owner", "crawler-engineer")
        run(self.board, "comment", "TEAM-1", "--author", "crawler-engineer", "--body-file", self.body_file("WORK-REPORT one"))
        run(self.board, "comment", "TEAM-1", "--author", "delivery-lead", "--body-file", self.body_file("Accepted."))
        run(self.board, "describe", "TEAM-1", "--body-file", self.body_file("New description."))
        meta, body, comments = board.parse_ticket(Path(run(self.board, "path", "TEAM-1")[1]).read_text())
        self.assertEqual(body, "New description.")
        self.assertIn("crawler-engineer\n\nWORK-REPORT one", comments)
        self.assertLess(comments.index("WORK-REPORT one"), comments.index("Accepted."))
        self.assertTrue(comments.startswith("## Comments"))

    def test_set_updates_fields_but_not_immutable_ones(self):
        run(self.board, "new", "--title", "A", "--owner", "human")
        run(self.board, "set", "TEAM-1", "branch", "ft/TEAM-1-a")
        run(self.board, "set", "TEAM-1", "blocked_by", "[TEAM-3, TEAM-4]")
        meta = board.parse_ticket(Path(run(self.board, "path", "TEAM-1")[1]).read_text())[0]
        self.assertEqual((meta["branch"], meta["blocked_by"]), ("ft/TEAM-1-a", ["TEAM-3", "TEAM-4"]))
        self.assertEqual(run(self.board, "set", "TEAM-1", "id", "X")[0], 1)

    def test_move_uses_git_mv_for_tracked_files(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        run(self.board, "new", "--title", "A", "--owner", "human")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", "init"], check=True)
        run(self.board, "move", "TEAM-1", "done")
        status = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain"],
                                capture_output=True, text=True, check=True).stdout
        self.assertIn("R  .board/2-todo/TEAM-1-a.md -> .board/6-done/TEAM-1-a.md", status)

    def test_missing_ticket_is_an_error(self):
        code, _, err = run(self.board, "show", "TEAM-99")
        self.assertEqual(code, 1)
        self.assertIn("no ticket TEAM-99", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
