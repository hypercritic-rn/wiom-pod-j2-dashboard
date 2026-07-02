# Customer POD — J2 Recharge → Exit renewal health

A two-part dashboard (new-customer journey + tenured base) that refreshes daily from Metabase.

- `refresh.py` — queries Metabase, writes `dashboard_data.json` (rolling windows relative to today, IST). No third-party packages, standard library only.
- `build.py` — reads `dashboard_data.json`, writes `index.html`.
- `.github/workflows/refresh.yml` — runs both daily (02:00 UTC / 07:30 IST) and commits the refreshed `index.html` + `dashboard_data.json` back to this private repo (no public Pages).

## Metrics

**New customer** (owner: activation) — NSM Day-43 retention (all installs); Driver 1 first-paid conversion (R7); Driver 2 first-renewal R0 by plan bucket.

**Tenured base** (owner: retention) — NSM active-base retention (rolling 30d, tenured only); Driver on-time R0 by plan bucket; guardrails % active days and 1-day plan %.

PAYG = recharge on a `combined_setting_id = 22` plan. Active = live plan or lapsed ≤15 days. New vs tenured split at 43 days from install.

## Setup

1. Add repo secret `METABASE_KEY` (Settings → Secrets and variables → Actions). This is the Metabase API key; it is never committed.
2. Trigger once: Actions → Refresh dashboard → Run workflow. If it succeeds, Metabase is reachable from GitHub's runners and it will run daily. If it fails on a connection/timeout, Metabase is internal-only — run `refresh.py` on an internal machine on a schedule instead (a self-hosted runner, or Windows Task Scheduler).
3. View: pull the repo and open `index.html`, or point an internal static server at it.

## Run locally

```
python refresh.py   # reads key from METABASE_KEY env var, else Desktop/.env
python build.py
# open index.html
```

## Requirements before this can go live

- **Metabase must be reachable from GitHub's cloud runners.** If `metabase.wiom.in` is VPN/internal-only, a GitHub-hosted runner cannot reach it — use a self-hosted runner inside the network, or run `refresh.py` on an internal box and commit the output.
- **GitHub Pages URLs are public** regardless of repo visibility (except GitHub Enterprise with access control). This page shows internal retention and customer counts, so confirm that is acceptable before publishing, or host privately.
