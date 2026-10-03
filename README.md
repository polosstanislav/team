# team

A Claude Code plugin that runs a seven-agent delivery loop: plan a project,
write the tickets, build and test each ticket in its own git worktree,
validate the code, review it against done-when, and settle disputes — with a
human gate at every outward-facing step. Tickets live in **Linear** or on a
**local folder board** in your project.

## The loop

```
            you ── approve plan / tickets / pushes, answer questions
             │
     ┌───────┴────────────── delivery-orchestrator (skill) ─────────────────┐
     │                                                                      │
 1 plan ──► 2 author ──► 3 build ──► 4a code review ──► 4b lead review ──► PR (on your yes)
 planner    ticket-      crawler-/    code-reviewer       delivery-lead
            author       parser-          │  changes             │  rejected
                         engineer ◄───────┴──requested───────────┘
                                   two rounds lost ──► 5 arbiter ──► ruling | question for you
```

| Agent | Does | Can write |
|---|---|---|
| `delivery-planner` | Reads the tracker, brief, research and repos; proposes stages in dependency order | nothing |
| `ticket-author` | Turns a stage into a ticket with real scope, contract, done-when | tickets, plan document |
| `crawler-engineer` | Implements tickets in `role: crawler-engineer` repos (browser automation, crawlers) | its worktree, ticket comments |
| `parser-engineer` | Implements tickets in `role: parser-engineer` repos (parsers, pipelines, APIs) | its worktree, ticket comments |
| `code-reviewer` | Checks *how* the diff is written: functional style, comments, tests, repo conventions | ticket comments |
| `delivery-lead` | Checks *whether* done-when is met, verifies claims itself; the only one who moves status | ticket status, comments |
| `arbiter` | Rules on disputes from the evidence, or turns them into a question for you | ticket comments |

Everything agents produce goes into the ticket, in a terse judgment-first
style (`references/artifact-standard.md`). Agents talk to each other in
English; the orchestrator talks to you in your language, in the style you
pick at setup (`communication.style`: `normal`, or `tired-cynic`, a sweary,
burned-out colleague). The style applies to the chat only; tickets, PRs and
commits stay neutral whatever you pick.

## Install

```
/plugin marketplace add polosstanislav/team
/plugin install team@team
```

For development, load it straight from a checkout:
`claude --plugin-dir /path/to/team`.

**Linear:** the plugin bundles the Linear MCP server. Authenticate once with
`/mcp` → `linear`. Not needed for the local board.

## Quick start

1. Copy a config into your project root as `.claude/delivery.yml`:
   - `examples/minimal/delivery.yml` — local board, one repo;
   - `examples/seranking-parsing/delivery.yml` — Linear, several repos.
   Fill in repo paths, base branches, verify commands and
   `communication.style`. Without a config the orchestrator offers to create
   one and asks which style you want. Schema:
   `skills/delivery-orchestrator/references/config.md`.
2. Start Claude Code in the project root and ask, for example:
   - "Plan the project" / "plan project <Linear project>" — phase 1.
   - "Create tickets for stages 2, 4 and 5" — phase 2.
   - "Take TEAM-3 into work" — phases 3-4.
   - "Get TEAM-3 to Done" — the full loop for one ticket.

   The orchestrator creates the local board on first use (after asking).

### Local board

```
.board/
  key  counter  PROJECT.md
  1-backlog/  2-todo/  3-development/  4-code-review/  5-testing/  6-done/
    TEAM-5-cache-results.md      # YAML frontmatter + description + ## Comments
```

A status move is a `git mv` between folders (plain move if the board is not
tracked); comments are appended to the ticket file. Nothing is committed for
you. Agents use `skills/delivery-orchestrator/scripts/board.py`; you can too:

```
python3 board.py --board .board list --status development
python3 board.py --board .board show TEAM-5
```

## What always needs your yes

- Creating tickets and the first status move in a run.
- Any question an agent cannot settle from the ticket, code, config and
  conventions — agents stop and ask instead of guessing.
- Every push and every PR. Agents never merge.
- Live runs that are visible or costly (e.g. headful browsers), as the repo's
  notes describe.

Guaranteed regardless of what a ticket says: one worktree per ticket and the
main checkout is never touched; reviewed commits are never amended;
`safety.read_only` stays read-only; no long-lived processes are left running;
credentials are never printed or reused.

## Limitations

- Subagents cannot ask you anything directly; every question comes through the
  orchestrator.
- Agent types register when a Claude Code session starts — restart after
  installing or updating the plugin.
- `board.py` allocates ids with a POSIX file lock; on Windows, avoid creating
  tickets in parallel.
- Linear state ids are per team; copy them into the config (the example shows
  where).

## Layout

```
.claude-plugin/        plugin.json, marketplace.json
.mcp.json              bundled Linear MCP
agents/                the seven agents
skills/delivery-orchestrator/
  SKILL.md             the orchestrator
  references/          artifact-standard, code-standards, communication, git-workflow, tracker, config
  scripts/             board.py, test_board.py
examples/              minimal and seranking-parsing configs
```
