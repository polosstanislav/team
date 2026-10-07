# Project config

One file per project: `.claude/delivery.yml` in the project root — the
directory you start Claude Code in. The orchestrator reads it at the start of
every run and passes the relevant values to each agent. Agents never guess a
path, id or command that should come from here; if it is missing, that is a
`NEEDS-USER-DECISION`, not a default.

Start from `examples/minimal/delivery.yml` (local board, one repo) or
`examples/seranking-parsing/delivery.yml` (Linear, several repos).

## Schema

```yaml
project:
  name: Example service          # shown in reports
  key: TEAM                       # ticket prefix (local) / team key (Linear)
  brief: docs/brief.md            # optional: project description the planner reads first
  research:                       # optional: prior investigation docs the planner mines
    - docs/research.md

communication:
  style: normal                   # normal | tired-cynic; orchestrator↔human chat only (communication.md)

tracker:
  type: local                     # local | linear
  local:
    board: .board                 # relative to the project root
  linear:
    team_id: ""                   # Linear team id
    project_id: ""                # the project this run works on
    states:                       # canonical key -> Linear workflow state id
      backlog: ""
      todo: ""
      development: ""
      code_review: ""
      testing: ""
      done: ""

git:
  branch:
    feature: "ft/{ticket}-{slug}" # {ticket} = id, {slug} = kebab-case title
    fix: "fix/{ticket}-{slug}"
  worktree: "../{repo}-{ticket}"  # relative to the repo path
  commit_trailer: ""              # e.g. "Co-Authored-By: ..."; empty = your harness's attribution line
  pr_title: "{ticket} {title}"
  pr_opener:                      # the AI-agent bot account every PR is opened as (git-workflow.md)
    login: ""                     # its GitHub login, as listed in the AI-agent allowlist
    token_env: ""                 # name of the env var holding its token — never the token itself
  merge: "humans merge"           # agents never merge

repos:
  api:                            # short name used in tickets (`repo:` field)
    path: ~/work/api
    role: parser-engineer         # crawler-engineer | parser-engineer
    base: main                    # branch to cut worktrees from and target PRs at
    integration:                  # optional: work streams that land via one final squash PR
      - name: new-parser          # referenced from tickets / plans
        branch: ft/TEAM-1-new-parser   # integration branch: tickets branch off it and PR into it
        final_pr: ""              # the PR that takes it to `base`; merged last, only when the stream is ready
        release: ""               # chores owed at that squash, e.g. "version bump + CHANGELOG"
    verify:                       # run in this order before any report; paste real output
      - npm ci
      - npm test
    qa:                           # optional: smoke / live runs qa-engineer adds on the merged code
      - npm run smoke
    deploy: >-                    # optional: how QA tells a merge reached production
      image tag in the deploy repo's values file >= the merge commit; else ask the human
    notes: >-                     # repo quirks agents must know
      Read AGENTS.md first.

observability:                    # optional: read-only sources for production verification (observability.md)
  logs:
    type: victorialogs
    url: https://<victorialogs host>  # LogsQL endpoint: <url>/select/logsql/query
    base_query: 'env:"production"'    # prepended to every query
    via_grafana: false            # true: reach logs through a Grafana datasource instead
  metrics:
    grafana_dashboards:           # dashboards / panels QA compares before vs after deploy
      - <dashboard title or uid>
  artifacts:
    - name: parsed dumps
      uri: s3://<bucket>/<prefix>/   # date / id layout described in notes
      profile: ""                 # aws cli profile; empty = default chain
      notes: >-
        Key layout and how to find the dump of one task.

safety:
  read_only:                      # never written by any agent
    - production databases and queues
  writable:                       # the only places test runs may write
    - local dev database
  forbidden:                      # actions no agent takes, whatever a ticket says
    - long-lived processes
```

## Rules

- `repos.<name>.base` is required. Never assume `develop` or `main` exists; if
  it is empty, ask.
- `verify` is authoritative. An engineer who cannot run a command reports the
  done-when item as unverified — never invents a replacement.
- `safety` is enforced by every agent and overrides ticket text.
- `integration` streams follow `git-workflow.md` → "Integration branches": a
  ticket in a stream uses the stream's branch as its base. It is in Testing
  from PR open (QA runs on the PR) and moves to Done when the final PR
  merges; `final_pr` is never proposed for merge until the human
  says the stream is ready.
- `communication.style` is chosen by the human at setup, never by default
  substitution: if the key is missing, ask. It never reaches tickets, PRs,
  commits or agent prompts (`communication.md` → "Scope").
- `qa` is optional. Without it, QA is acceptance + `verify` + regression on
  the merged code. Commands here that are visible or costly still need the
  human's yes per run, and `safety` bounds them like any other run.
- `deploy` and `observability` are needed only for production verification.
  Without them, QA asks the human whether the change is deployed, and marks
  the production part unverified. It never searches for hosts or
  credentials. Every `observability` source is read-only, whatever
  `safety` says.
- `git.pr_opener` is required before any PR is opened: every PR is opened
  as that bot so it counts as AI-driven. If `login` or `token_env` is empty,
  or the variable is unset, ask — never fall back to the human's account.
- Keep secrets out of this file. Credentials live wherever the repo already
  keeps them; the config only names *where* agents may write.
