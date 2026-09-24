# Git workflow

Branch names, bases, worktree paths and the commit trailer come from the
project config (`git:` and `repos.<name>.base`). The rules below apply to
every repo.

## One worktree per ticket

The main checkout of each repo is the human's workspace and may be dirty on
an unrelated branch. **Never** `checkout`, `stash`, `reset`, `clean` or commit
in it.

The orchestrator creates the worktree and branch before delegating:

```
git -C <repo> fetch origin <base>
git -C <repo> worktree add -b <branch> <worktree> origin/<base>
git -C <worktree> branch --unset-upstream   # a stray `git push` must not target <base>
```

`<branch>` follows `git.branch.feature` / `git.branch.fix`; `<worktree>`
follows `git.worktree`. If the repo needs installed dependencies, follow
`repos.<name>.notes` (e.g. symlink the main checkout's dependency dir, and
ignore the symlink via `$(git rev-parse --git-common-dir)/info/exclude`). If a
ticket changes the dependency manifest, stop and ask.

Engineers work only inside their worktree. A verification run that needs no
branch uses a detached worktree at the commit under test, removed afterwards.

## Commits

Allowed on your own ticket branch, in your own worktree. English, ticket id
first, imperative: `TEAM-12 Add retry to the fetcher`. Small reviewable
commits. **Never amend or rewrite a commit a reviewer has already seen** —
follow-ups are new commits. End every message with `git.commit_trailer`, or
your harness's attribution line if the config leaves it empty.

When a change must be provably behaviour-neutral, split it: one commit with
the refactor alone (old specs green there), one with new behaviour or specs.

## Push and PR — only after the human confirms

Engineers never push. When the lead has accepted the work, the orchestrator
asks the human about that specific PR; only on an explicit yes does it push
and open it. Updating an already-approved PR with follow-up commits counts as
approved when the human asked for the follow-ups in that PR.

Before pushing: branch clean, rebased or cleanly mergeable onto the current
`origin/<base>` (check with `git merge-tree --write-tree origin/<base> HEAD`),
trailer present, nothing unrelated in the diff.

- Title: `git.pr_title`.
- Description: why, the decisions and their alternatives, evidence, link to
  the ticket — what the diff cannot show, in artifact-standard voice. If the
  repo has a PR template or a PR-creation skill, use it.
- Target `repos.<name>.base`. Agents never merge.
- After the human merges: remove the worktree, delete the local and remote
  ticket branch, and link the merge commit on the ticket.

## Never

- Push to or rewrite a protected branch (`main`, `master`, `develop`,
  `release-*`, or anything `base`).
- Force-push, except `--force-with-lease` on your own ticket branch.
- Print a remote URL or any credential. Remotes can embed tokens; if you must
  show one, strip userinfo: `git remote get-url origin | sed -E 's#//[^@/]*@#//#'`.
- Use a credential you found (in a remote URL, a config, a log) for anything
  it was not given to you for.
