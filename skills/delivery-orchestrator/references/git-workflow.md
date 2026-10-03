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
follows `git.worktree`; `<base>` is the ticket's base — `repos.<name>.base`, or
the integration branch when the ticket belongs to one (see below).

**Dependency dirs.** If the repo needs installed dependencies, follow
`repos.<name>.notes`. A JS `node_modules` may be symlinked from the main
checkout (ignore the symlink via `$(git rev-parse --git-common-dir)/info/exclude`).
**Never symlink PHP `vendor/`**: Composer's autoloader resolves the project
root from vendor's real path, so tests would silently load the main
checkout's `src`. Copy it (`cp -a`) and check that autoload resolves a class
from the worktree before handing it over. If a ticket changes the dependency
manifest, stop and ask.

**Shell pitfall.** In zsh, `"$VAR:suffix"` applies `:s`, `:h`, `:t`… as
modifiers — write `"${VAR}:path"` (e.g. `git show "${REF}:src/file"`).

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

## Integration branches

A repo may declare an integration branch for a body of work
(`repos.<name>.integration`, see `config.md`). For tickets in that stream:

- Branch off the integration branch's **remote** tip and PR into it — never
  into the default branch. A local copy of it may be stale; always use
  `origin/`.
- A ticket is in **Testing** from the moment its PR opens, and QA runs on
  that PR. A merge into the integration branch leaves it in Testing. The
  ticket moves to Done when the stream's final PR merges into the default
  branch.
- The integration branch reaches the default branch as **one final squash
  PR**, merged only when the whole stream is ready. Never propose merging it
  earlier. Release chores owed at that squash (version bump, CHANGELOG) are
  recorded on the tickets so they are not lost.

**Stacked branches** (a ticket branched off another unmerged ticket branch)
only when the human chooses it. After the lower PR squash-merges, rebuild the
upper branch from the new base tip before its review or PR.

**After any squash merge, verify by content, not ancestry.** Squash commits
break ancestry, so `merge-base --is-ancestor` and commit counts mislead.
Compare trees: `git diff --quiet <reviewed-head> origin/<base> -- <paths>`
(or equal tree SHAs). Do this before moving a ticket after a merge and before
deleting its branch.

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
- Once the PR is open, `qa-engineer` tests it and comments its report on the
  PR. That comment is the only thing an agent writes on a PR without a
  per-action yes. Agents never approve, request changes or merge. Any
  commit pushed after a QA pass needs a new QA round before merge.
- After the human merges: verify the merged content (see above), remove the
  worktree, delete the local and remote ticket branch, and link the merge
  commit on the ticket.

## Before pushing follow-ups to an existing PR

Check the PR is still **open** — `gh pr view <n> --json state,mergedAt` — not
just that its branch exists. A PR that was (squash-)merged while follow-ups
were in review leaves a dead branch: a push lands there and never reaches the
base. If it merged: confirm the base lacks exactly the follow-up commits
(content comparison), branch fresh from the base tip, cherry-pick them, and
open a new PR — after the human confirms. Correct any report or ticket
comment that claimed the push reached the PR.

## Never

- Push to or rewrite a protected branch (`main`, `master`, `develop`,
  `release-*`, or anything `base`).
- Force-push, except `--force-with-lease` on your own ticket branch.
- Print a remote URL or any credential. Remotes can embed tokens; if you must
  show one, strip userinfo: `git remote get-url origin | sed -E 's#//[^@/]*@#//#'`.
- Use a credential you found (in a remote URL, a config, a log) for anything
  it was not given to you for.
