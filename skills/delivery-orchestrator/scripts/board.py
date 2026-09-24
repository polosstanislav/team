#!/usr/bin/env python3
"""Local folder board: status folders hold one markdown file per ticket.

    .board/
      key            ticket prefix, e.g. TEAM
      counter        next ticket number
      PROJECT.md     project brief and stage plan
      1-backlog/ 2-todo/ 3-development/ 4-code-review/ 5-testing/ 6-done/
        TEAM-5-cache-results.md

A status move is a `git mv` when the ticket file is tracked by git, a plain
rename otherwise. The script never commits. Stdlib only.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import fcntl
except ImportError:  # non-POSIX: allocation is then not safe under parallel writers
    fcntl = None

STATUSES = ("backlog", "todo", "development", "code_review", "testing", "done")
FOLDERS = {s: f"{i}-{s.replace('_', '-')}" for i, s in enumerate(STATUSES, start=1)}
FIELDS = ("id", "title", "owner", "repo", "branch", "blocked_by", "created", "updated")
COMMENTS_HEADING = "## Comments"

BODY_TEMPLATE = """<One sentence: what this ticket delivers.>

**Scope**
- <concrete change, with file/repo path>

**Done when**
- [ ] <observable, checkable>
"""

PROJECT_TEMPLATE = """# Project

<What this project delivers, in one paragraph. The planner reads this file
first; keep the original scope as numbered points.>

## Stage plan

<Written by ticket-author when asked for the plan document.>
"""


class BoardError(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(title, limit=50):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:limit].rstrip("-") or "ticket"


# --- ticket file format ----------------------------------------------------

def parse_value(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [item.strip() for item in raw[1:-1].split(",") if item.strip()]
    return raw


def format_value(value):
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(value) + "]"
    return "" if value is None else str(value)


def parse_ticket(text):
    """Split a ticket file into (frontmatter dict, body, comments section)."""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not match:
        raise BoardError("ticket file has no frontmatter")
    meta = {
        key.strip(): parse_value(value)
        for key, _, value in (line.partition(":") for line in match.group(1).splitlines())
        if key.strip()
    }
    rest = match.group(2)
    body, sep, comments = rest.partition("\n" + COMMENTS_HEADING + "\n")
    return meta, body.strip("\n"), (sep + comments).strip("\n") if sep else ""


def render_ticket(meta, body, comments):
    keys = list(FIELDS) + [k for k in meta if k not in FIELDS]
    front = "\n".join(f"{k}: {format_value(meta.get(k, ''))}" for k in keys)
    parts = [f"---\n{front}\n---", body.strip("\n")]
    parts.append(comments if comments else COMMENTS_HEADING)
    return "\n\n".join(parts) + "\n"


# --- board layout ----------------------------------------------------------

def board_key(board):
    key_file = board / "key"
    if not key_file.exists():
        raise BoardError(f"not a board (no key file): {board}")
    return key_file.read_text().strip()


def all_tickets(board):
    """Yield (status, path) for every ticket file, in status then name order."""
    for status in STATUSES:
        folder = board / FOLDERS[status]
        for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            yield status, path


def find_ticket(board, ticket_id):
    matches = [(s, p) for s, p in all_tickets(board) if p.name.startswith(ticket_id + "-")]
    if not matches:
        raise BoardError(f"no ticket {ticket_id}")
    if len(matches) > 1:
        raise BoardError(f"ticket {ticket_id} exists in several folders: {[str(p) for _, p in matches]}")
    return matches[0]


def allocate_number(board):
    counter = board / "counter"
    with open(counter, "r+") as handle:
        if fcntl:
            fcntl.flock(handle, fcntl.LOCK_EX)
        number = int(handle.read().strip() or "1")
        handle.seek(0)
        handle.write(f"{number + 1}\n")
        handle.truncate()
    return number


def is_tracked(path):
    result = subprocess.run(
        ["git", "-C", str(path.parent), "ls-files", "--error-unmatch", path.name],
        capture_output=True,
    )
    return result.returncode == 0


def rename(src, dst):
    if is_tracked(src):
        subprocess.run(["git", "-C", str(src.parent), "mv", str(src), str(dst)], check=True)
        return
    src.rename(dst)


# --- commands --------------------------------------------------------------

def cmd_init(board, args):
    if not args.key or not re.fullmatch(r"[A-Z][A-Z0-9]*", args.key):
        raise BoardError("init needs --key in upper case, e.g. --key TEAM")
    if (board / "key").exists():
        raise BoardError(f"board already initialised: {board}")
    for folder in FOLDERS.values():
        (board / folder).mkdir(parents=True, exist_ok=True)
    (board / "key").write_text(args.key + "\n")
    (board / "counter").write_text("1\n")
    project = board / "PROJECT.md"
    if not project.exists():
        project.write_text(PROJECT_TEMPLATE)
    return str(board)


def cmd_new(board, args):
    status = validate_status(args.status)
    ticket_id = f"{board_key(board)}-{allocate_number(board)}"
    stamp = now()
    meta = {
        "id": ticket_id,
        "title": args.title,
        "owner": args.owner,
        "repo": args.repo or "",
        "branch": "",
        "blocked_by": args.blocked_by or [],
        "created": stamp,
        "updated": stamp,
    }
    body = Path(args.body_file).read_text() if args.body_file else BODY_TEMPLATE
    path = board / FOLDERS[status] / f"{ticket_id}-{slugify(args.title)}.md"
    path.write_text(render_ticket(meta, body, ""))
    return str(path)


def cmd_list(board, args):
    wanted = validate_status(args.status) if args.status else None
    selected = [(s, parse_ticket(p.read_text())[0], p) for s, p in all_tickets(board) if wanted in (None, s)]
    return "\n".join(f"{meta.get('id', p.stem)}\t{s}\t{meta.get('title', '')}" for s, meta, p in selected)


def cmd_show(board, args):
    status, path = find_ticket(board, args.id)
    return f"status: {status}\npath: {path}\n\n{path.read_text()}"


def cmd_path(board, args):
    return str(find_ticket(board, args.id)[1])


def cmd_move(board, args):
    target = validate_status(args.status)
    status, path = find_ticket(board, args.id)
    if status == target:
        raise BoardError(f"{args.id} is already in {target}")
    update_file(path, lambda meta, body, comments: ({**meta, "updated": now()}, body, comments))
    dst = board / FOLDERS[target] / path.name
    rename(path, dst)
    return f"{args.id}: {status} -> {target}"


def cmd_comment(board, args):
    _, path = find_ticket(board, args.id)
    text = Path(args.body_file).read_text().strip("\n")
    stamp = now()

    def append(meta, body, comments):
        section = comments or COMMENTS_HEADING
        return {**meta, "updated": stamp}, body, f"{section}\n\n### {stamp} {args.author}\n\n{text}"

    update_file(path, append)
    return f"{args.id}: comment by {args.author} at {stamp}"


def cmd_describe(board, args):
    _, path = find_ticket(board, args.id)
    text = Path(args.body_file).read_text()
    update_file(path, lambda meta, body, comments: ({**meta, "updated": now()}, text, comments))
    return f"{args.id}: description replaced"


def cmd_set(board, args):
    if args.field in ("id", "created"):
        raise BoardError(f"{args.field} is immutable")
    _, path = find_ticket(board, args.id)
    value = parse_value(args.value) if args.field == "blocked_by" else args.value
    update_file(path, lambda meta, body, comments: ({**meta, args.field: value, "updated": now()}, body, comments))
    return f"{args.id}: {args.field} = {format_value(value)}"


def update_file(path, change):
    meta, body, comments = change(*parse_ticket(path.read_text()))
    path.write_text(render_ticket(meta, body, comments))


def validate_status(status):
    if status not in STATUSES:
        raise BoardError(f"unknown status {status!r}; use one of {', '.join(STATUSES)}")
    return status


# --- CLI -------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--board", default=os.environ.get("DELIVERY_BOARD", ".board"),
                        help="board directory (default: $DELIVERY_BOARD or ./.board)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create the board")
    p.add_argument("--key", required=True, help="ticket prefix, e.g. TEAM")
    p.set_defaults(run=cmd_init)

    p = sub.add_parser("new", help="create a ticket; prints its path")
    p.add_argument("--title", required=True)
    p.add_argument("--owner", required=True, help="role that owns it, e.g. crawler-engineer or human")
    p.add_argument("--repo")
    p.add_argument("--status", default="todo")
    p.add_argument("--blocked-by", nargs="*", dest="blocked_by")
    p.add_argument("--body-file")
    p.set_defaults(run=cmd_new)

    p = sub.add_parser("list", help="id, status, title per line (tab-separated)")
    p.add_argument("--status")
    p.set_defaults(run=cmd_list)

    for name, run, helptext in (("show", cmd_show, "status, path and full file"), ("path", cmd_path, "file path")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("id")
        p.set_defaults(run=run)

    p = sub.add_parser("move", help="move a ticket to another status")
    p.add_argument("id")
    p.add_argument("status")
    p.set_defaults(run=cmd_move)

    p = sub.add_parser("comment", help="append a comment")
    p.add_argument("id")
    p.add_argument("--author", required=True, help="role writing the comment")
    p.add_argument("--body-file", required=True)
    p.set_defaults(run=cmd_comment)

    p = sub.add_parser("describe", help="replace the description (comments are kept)")
    p.add_argument("id")
    p.add_argument("--body-file", required=True)
    p.set_defaults(run=cmd_describe)

    p = sub.add_parser("set", help="set a frontmatter field (owner, repo, branch, blocked_by, title)")
    p.add_argument("id")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(run=cmd_set)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        output = args.run(Path(args.board).expanduser().resolve(), args)
    except BoardError as error:
        print(f"board: {error}", file=sys.stderr)
        return 1
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
