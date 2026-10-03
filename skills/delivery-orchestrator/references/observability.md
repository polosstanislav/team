# Observability: verifying in production

`qa-engineer` uses this to verify a merged fix where it runs. Every source is
**read-only**. Agents query, sample and read. They never write, delete,
re-run jobs, change dashboards or alerts, or push tasks to production queues.
`safety` in the config wins over anything here.

Endpoints, datasources and buckets come from `observability` in
`.claude/delivery.yml`. Never guess a host. If the config lacks a source,
the item is unverified: ask the human, do not search for credentials.

## Logs: VictoriaLogs

HTTP API, LogsQL:

```
curl -s '<logs.url>/select/logsql/query' \
  --data-urlencode 'query=<logs.base_query> AND <your filter>' \
  --data-urlencode 'start=<RFC3339 or epoch>' --data-urlencode 'end=<…>' \
  --data-urlencode 'limit=1000'
```

The response is newline-delimited JSON. Aggregate it locally (`jq`, a short
script) instead of reading it by eye.

- **Prove the new code runs.** Count a log line only the new code emits. If
  there is none, the ticket should have added one; note its absence as a
  gap.
- **Cohorts during a rolling deploy.** Group lines by trace id, mark each
  trace new or old by that line, and compare the metric across the cohorts.
  This beats a blended number.
- **Rollout progress.** Pods running the new image against the total.
  Container restarts above 0 flag a crash loop.
- **Lag.** Ingestion lags. Use an offset window (e.g. `now-12m..now-4m`) for
  rates. A `now-5m..now` window can read zero.
- Use `logs.via_grafana: true` when the logs are reachable only through a
  Grafana datasource. Then query through the Grafana tools instead.

## Metrics: Grafana

Use the Grafana MCP tools: `search_dashboards`, `get_dashboard_summary`,
`get_dashboard_panel_queries`, `run_panel_query`, `query_prometheus`.

- Compare windows of equal length before and after the deploy. Name the
  panel, the query and both numbers.
- A dashboard mean moves only after the pre-deploy data ages out of its
  window. Say so instead of reading "no change".
- Name confounders you can see, such as a traffic spike or an upstream
  outage, that the change did not cause.
- Link panels with `generate_deeplink`. Do not paste screenshots.

## Dumps: S3

Raw, parsed or intermediate dumps, as `artifacts` lists them:

```
aws s3 ls  s3://<bucket>/<prefix>/<date>/ [--profile <artifacts.profile>]
aws s3 cp  s3://<bucket>/<key> <scratch dir>/
```

- Take a **bounded sample** produced after the deploy, e.g. 10-50 objects,
  each matching the fixed case. Never sync a whole prefix.
- Re-check the fixed behaviour on them. Where possible, run the merged
  parser or check from your scratch worktree.
- Keep downloads in your scratch directory and delete them when you finish.
  Dumps may hold customer queries or personal data. Report counts, object
  keys and short sanitized fragments only.
- If a permission classifier or policy blocks reading a dump, stop and say
  so. Do not work around it.

## What a production verdict needs

- Evidence that the fixed code is deployed.
- At least one direct observation after the deploy: logs, metrics or dumps.
  Use more than one when the ticket's done-when names them.
- The query, panel or object keys used, the window, before and after numbers,
  and the sample size.

Without these, the production part is **unverified** and the ticket stays in
testing.
