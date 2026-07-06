# Customer POD — J2 Recharge → Exit — Metric & View Spec

Status: **New-customer (§3) + Tenured (§4) = LOCKED & built.** Only plan-behaviour (§5) still open.
✔ = agreed · ❓ = open decision (see §7).

New-side build notes: payment = renewal 5-min funnel (~74%, not raw ratio); Day-43 & conversion graphs show both cohort + event date; D2 has NO bucket-bars section (28d headline only).

---

## 1. Principle
Renewal health, so an owner can see if action is needed. Two cohorts split only by tenure. NSMs are lagging outcomes; drivers are leading signals; inputs are daily levers. Descriptive, no editorialising.

## 2. Global definitions ✔
- **Base:** complete Home broadband — `store_group_id=0`, `otp='DONE'`, `device_limit>1`, `mobile>'5999999999'`, test partners/mobiles excluded. All plan types (PAYG, legacy, migrated). Excludes WiomNet.
- **Tenure split:** 43 calendar days from install. New `<43d`, tenured `≥43d`. (Not recharge count.)
- **Active** (for retention checkpoints): plan live at the checkpoint OR last plan ended ≤15 days ago.
- **New install:** first-ever recharge on a NAS with `TRANSACTION_ID ILIKE '%booking_payment%'` (post-26-Jan).
- **Plan bucket:** 1d / 7d / 28d / Other, from `t_plan_configuration.time_limit`.
- **IST** everywhere (+330 min). Refresh **daily**.

## 3. New customer  (owner: activation)
| Tier | Metric | Definition | Display | Cohort basis |
|---|---|---|---|---|
| **NSM** | Day-43 retention | % of install cohort active at day 43. Denominator = ALL installs. | Headline = **yesterday** + **MTD-through-yesterday**. Trend daily/weekly toggle. | install date |
| **Driver 1** | First-paid conversion | % of installs making first paid recharge within 7d of free-trial expiry. | **Daily headline** (last matured day) + 30d secondary. Daily/weekly toggle trend. | free-trial-expiry date |
| **Driver 2** | Expiry-day renewals | on-time renewal rate (next plan starts ≤ expiry) of new-customer paid plans, **ALL plans blended** (not per-bucket — 28d-only was ~6/day, too thin). | **Daily headline** (~105/day, last complete day) + 30d secondary. Daily/weekly toggle trend, **last 30 days**. | expiry date |
| **Input** | Renewal-payment success ✔ | 5-min funnel: attempt = `checkout_page_loaded`, converts if `payment_success_page_loaded` within 5 min. New-customer renewal payments. **`FUNNEL_STEP` in (`renewal`,`renewal_payment_flow`) — checkout & success carry different labels, need both.** Attempts deduped per NAS per 5-min clock window. ~74%. | Headline + weekly trend. | checkout date |
| **Input** | App-open near expiry | % of new-customer expiries with an app open ≤3d before expiry. | 30d headline + daily/weekly toggle (last 30d). | expiry date |

Renewal-payment input display: 30d headline + daily/weekly toggle (last 30d). **All new-side charts: daily + toggle, last 30 days, fixed 0–100% y-axis.** Bottom of page carries a Metric-definitions + Method block.

Dropped: Day-30 active (redundant with NSM); first-renewal-R0 (leaked short plans); nudge open (whole-base only, can't new-scope); data usage (removed by request).

## 4. Tenured  (owner: retention) — BUILT ✔ (same standard as new: daily headline + daily/weekly toggle, last 30d, 0–100 axis, real dates)
| Tier | Metric | Definition | Display |
|---|---|---|---|
| **NSM** | Active-base retention | rolling 30-day: active tenured today ÷ active 30d ago. | daily headline (yesterday) + MTD (of base active on the 1st, share active yesterday). |
| **Driver 1** | On-time renewal | of tenured expiries (all plans), share whose next plan starts ≤ expiry. | daily headline + 30d secondary + toggle. |
| **Driver 2** | Grace recovery | of tenured expiries that MISSED on-time, share recharging within 15d (before churn). Matures 15d after expiry. | daily headline + 30d secondary + toggle. |
| **Input** | Renewal-payment success | 5-min funnel, tenured-scoped. | 30d headline + daily toggle. |
| **Input** | App-open near expiry | tenured expiries with app open ≤3d before expiry. | 30d headline + daily toggle. |
| **Guardrail** | % active days | avg coverage + share under 30% (rolling 30d). | headline. |

Decomposition: `active-base retention ≈ on-time renewal + (missed × grace recovery)`. (1-day plan % guardrail REMOVED from tenured.)

**Guardrail (BOTH cohorts): On paid plan.** Base = the cohort's **active (NSM) base** (a paid plan live, or lapsed ≤15d) — so it decomposes the retained customers. Split MECE: on paid plan (live) / lapsed R0–7d / lapsed R7–15d; sums to 100%. Headline = % on paid plan + the lapse split; single-line trend on % on paid plan (daily/weekly toggle). New base = customers with ≥1 paid recharge. New ~85% (10/5); tenured ~88% (8/4).

## 5. Plan behaviour  (own tab, both cohorts) ❓
Descriptive plan mix — no upgrade/downgrade judgment.
- New: plan chosen at 1st renewal → 2nd renewal, and transitions.
- Tenured: plan mix — display TBD.
- ❓ exact viz (transition table vs stacked bars).

## 6. View / display rules ✔ (except noted)
- Tabs: **New customer** · **Tenured base** · ❓ **Plan behaviour**.
- NSM headline: daily (yesterday) + MTD beside it.
- Drivers/inputs: headline + weekly trend (cohorts small → weekly, no daily noise).
- Trends: daily/weekly toggle only where the base is large (NSMs); weekly-only elsewhere. Every trend labelled with its **cohort basis**.
- **Lagged cohort metrics show BOTH dates.** For Day-43 retention (and any cohort measured at a lag), the point/tooltip must show the cohort date *and* the event/checkpoint date, e.g. "install 20 May → day-43 02 Jul". The headline (yesterday) is by the *event* date; the graph x-axis is by *cohort* date — surface both so the two aren't confused.
- Bucket metrics: bars 1d/7d/28d/Other, 28-day headline.
- Colours: NSM navy · driver teal · input purple · guardrail gold.
- Partial trailing periods drawn hollow.

## 7. OPEN DECISIONS — to lock before building
1. **Tenured NSM display** — daily+MTD like new, or yesterday-only? MTD for a rolling ratio needs a definition (avg of the month's daily values, or month-start→yesterday retention).
2. **Tenured drivers/inputs** — R0 driver: add a trend? Which inputs on the tenured tab (payment/app-open tenured-scoped), or none?
3. **Guardrails placement** — % active days and 1-day% live on tenured only, or shown for both / globally?
4. **Counter-metrics** — do we want an explicit counter per NSM (e.g. activation quality for new), or are guardrails enough?
5. **Plan-behaviour viz** — transition table, stacked bars, or flow? Same for both cohorts?
6. **D2 thin base** — new-customer 28-day bucket is ~470 expiries/30d, so its weekly trend is jumpy. Keep 28d headline, or headline a sturdier all-bucket number?
7. ~~Payment denominator~~ **RESOLVED** — was double-firing (3,387 raw → 1,198 attempts). Now a 5-min funnel on renewal `FUNNEL_STEP`, deduped attempts, = ~74%. Locked in §3.
8. **Nudge** — leave dropped, or invest in a new-scoped build from raw CleverTap (campaign-match in JSON, fiddly)?

## 8. Verified data sources
- `T_ROUTER_USER_MAPPING`, `T_PLAN_CONFIGURATION` (combined_setting_id=22 = 13 PAYG plans).
- Payment: `PUBLIC.CT_CUSTOMER_PAYG_PAYMENT_EVENTS_MV` (checkout/success), join `NASID_LONG`.
- App-open: `PUBLIC.CT_CUSTOMER_APP_LAUNCH` (`NASIDLONG`, timestamp).
- Nudge (whole-base only): `DBT_CUSTOMER_POD.FCT_PRE_EXPIRY_NUDGE_DAILY`.
- Usage: `DBT.FCT_FREE_TRIAL_USAGE_GB`, `DBT.HOURLY_USAGE_PRORATED` (PUBLIC `_DT` is dead).
- **Note:** a maintained `DBT_CUSTOMER_POD` layer exists (M1, MoM, R0, etc.) built to the *original* sheet defs — diverges from ours (their M1 71% vs our 91%). We are NOT adopting it; keep our definitions.
