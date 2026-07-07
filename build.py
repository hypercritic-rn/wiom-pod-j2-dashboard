# -*- coding: utf-8 -*-
"""Read dashboard_data.json, write index.html — a 2-part dashboard
(Part 1 New customer, Part 2 Tenured base). No hedging copy, terse."""
import json, os, datetime
def fmtd(iso, addd=0, fmt='%d %b'):
    try: return (datetime.date.fromisoformat(iso[:10])+datetime.timedelta(days=addd)).strftime(fmt).lstrip('0')
    except Exception: return iso
def _lower(o):
    if isinstance(o,list): return [_lower(x) for x in o]
    if isinstance(o,dict): return {k.lower():_lower(v) for k,v in o.items()}
    return o
D = _lower(json.load(open(os.path.join(os.path.dirname(__file__),"dashboard_data.json"))))

NAVY="#14284a"; TEAL="#1f7a70"; GOLD="#c68a1a"; RED="#c0392b"; SUB="#5b6b82"; INPUT="#6f5ec7"
def num(n):
    try: return "{:,}".format(int(round(float(n))))
    except: return str(n)

MON={'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}
def wk(s):
    return MON.get(s[5:7],s[5:7])+" "+s[8:10] if (isinstance(s,str) and len(s)==10 and s[4]=='-') else str(s)

def series(rows):
    return [{"date":r["wk"],"v":float(r["pct"]),
             "num":int(float(r.get("num",r["den"]))),"den":int(float(r["den"])),
             **({"cohort":r["cohort"]} if r.get("cohort") else {}),
             **({"l07":float(r["l07"]),"l7":float(r["l7"])} if r.get("l07") is not None else {})} for r in rows]

# ---- assemble the two parts ----
nsm_new = D["new_nsm_daily"][-1]   # last point = yesterday's cohort (series now excludes today's immature one)
nsm_mtd = D["new_nsm_mtd"]         # month-to-date through yesterday
d1 = D["new_d1_headline"]          # 30d aggregate (secondary, stable)
d1d = D["new_d1_daily"][-1]        # last complete day (daily headline)
d2d = D["new_d2_daily"][-1]        # last complete expiry day, ALL plans (daily headline)
d2_30 = D["new_d2_headline"]       # 30d all-plan aggregate (secondary, stable)
ten = D["ten_nsm_daily"][-1]       # yesterday's rolling-30 active-base value (series excludes today)
ten_mtd = D["ten_nsm_mtd"]         # month-to-date base retention
td1d = D["ten_d1_daily"][-1]; td1_30 = D["ten_d1_headline"]        # on-time renewal (daily + 30d)
td2d = D["ten_d2_daily"][-1]; td2_30 = D["ten_d2_headline"]        # grace recovery (daily + 30d)
tpay = D["ten_pay_headline"]; tapp = D["ten_appopen_headline"]; tapp_post = D["ten_appopen_post_headline"]   # tenured inputs (30d)
gad = D["guard_activedays"]
gp_new = D["new_paidstat_headline"]              # 30d aggregate (new daily base ~27, use stable)
gp_ten = D["ten_paidstat_daily"][-1]             # tenured yesterday (base ~91k, stable)

SER = {
 "new_nsm": {"legacy":85,"band":None,"legacyLabel":"Legacy M1 ~85%","gran":"daily","agg":"sum","toggle":True,"basis":"x = day-43 date · last 30 days · cohort installed 43d earlier","points":series(D["new_nsm_daily"])},
 "new_d1":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"x = free-trial-expiry date · matured 7d","eventoff":7,"eventlbl":"+7d","points":series(D["new_d1_daily"])},
 "new_d2":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"all plans · by expiry date · last 30 days","points":series(D["new_d2_daily"])},
 "in_pay":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"new customers · by checkout date · last 30 days","points":series(D["in_pay_daily"])},
 "in_appopen":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"new · ≤3d before expiry · last 30 days","points":series(D["in_appopen_daily"])},
 "in_appopen_post":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"new · ≤3d after expiry · matured 3d","points":series(D["in_appopen_post_daily"])},
 "ten_nsm": {"legacy":90,"band":[85,95],"legacyLabel":"Legacy 85–95%","gran":"daily","agg":"sample","toggle":True,"basis":"by report date · rolling 30d · last 30 days","points":series(D["ten_nsm_daily"])},
 "ten_d1":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"tenured · all plans · by expiry date · last 30 days","points":series(D["ten_d1_daily"])},
 "ten_d2":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"tenured lapsers · by expiry date · matured 15d","points":series(D["ten_d2_daily"])},
 "ten_pay": {"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"tenured · by checkout date · last 30 days","points":series(D["ten_pay_daily"])},
 "ten_appopen":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"tenured · ≤3d before expiry · last 30 days","points":series(D["ten_appopen_daily"])},
 "ten_appopen_post":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sum","toggle":True,"basis":"tenured · ≤3d after expiry · matured 3d","points":series(D["ten_appopen_post_daily"])},
 "new_paidstat":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sample","toggle":True,"basis":"of day-43-active customers · paid / R0–7 / R7–15","extra":[["l07","R0–7","#5b6b82"],["l7","R7–15","#c0392b"]],"points":series(D["new_paidstat_daily"])},
 "ten_paidstat":{"legacy":None,"band":None,"legacyLabel":None,"gran":"daily","agg":"sample","toggle":True,"basis":"of NSM-retained customers · paid / R0–7 / R7–15","extra":[["l07","R0–7","#5b6b82"],["l7","R7–15","#c0392b"]],"points":series(D["ten_paidstat_daily"])},
}

def bars(rowset, accent):
    order={"1d":0,"7d":1,"28d":2,"Other":3}
    bk=lambda r:r.get("bucket",r.get("wk"))
    rws=sorted(rowset,key=lambda r:order.get(bk(r),9))
    mx=max(float(r["pct"]) for r in rws) or 1
    h=""
    for r in rws:
        p=float(r["pct"]); w=max(3,p/max(mx,60)*100)
        h+=f"""<div class="bar"><div class="blab">{bk(r)}</div>
        <div class="btrk"><div class="bfill" style="width:{w:.0f}%;background:{accent}"></div></div>
        <div class="bval">{p:.1f}%<span class="bden">{num(r['num'])}/{num(r['den'])}</span></div></div>"""
    return h

def kpi(key, tier, accent, name, val, det, sub, trend=True):
    tclass="metric" if trend else "metric notrend"
    click=f"onclick=\"showTrend('{key}')\"" if trend else ""
    cue='<span class="cue">trend ↗</span>' if trend else ''
    return f"""<div class="{tclass}" data-k="{key}" style="--a:{accent}" {click}>
      <div class="mtier">{tier}</div><div class="mname">{name}</div><div class="msub">{sub}</div>
      <div class="mval">{val}</div><div class="mdet">{det}</div><div class="mcue">{cue}</div></div>"""

# Part 1 cards
p1 = kpi("new_nsm","NSM · Day 43 · daily",NAVY,"Day-43 retention",f"{float(nsm_new['pct']):.1f}%",
         f"{num(nsm_new['num'])} of {num(nsm_new['den'])} · day-43 {fmtd(nsm_new['wk'])} · MTD {float(nsm_mtd['pct']):.1f}%","Owner: activation")
p1 += kpi("new_d1","Driver · convert · daily",TEAL,"First-paid conversion",f"{float(d1d['pct']):.1f}%",
          f"{num(d1d['num'])} of {num(d1d['den'])} in 7d · {fmtd(d1d['wk'])} · 30d {float(d1['pct']):.1f}%","Leading, ~9-day lag")
p1 += kpi("new_d2","Driver · renew · daily",TEAL,"Expiry-day renewals",f"{float(d2d['pct']):.1f}%",
          f"{num(d2d['num'])} of {num(d2d['den'])} renewed on time · {fmtd(d2d['wk'])} · 30d {float(d2_30['pct']):.1f}%","Renewal rate · all plans")

# Part 1 inputs (new customers only)
ip=D["in_pay_headline"]; ia=D["in_appopen_headline"]; ipp=D["in_appopen_post_headline"]
p1_in  = kpi("in_pay","Input · payment",INPUT,"Renewal-payment success",f"{float(ip['pct']):.1f}%",
          f"{num(ip['num'])} of {num(ip['den'])} attempts succeed in 5 min","Mechanical gate → D1/D2")
p1_in += kpi("in_appopen","Input · app open",INPUT,"App-open pre-expiry",f"{float(ia['pct']):.1f}%",
          f"{num(ia['num'])} of {num(ia['den'])} open app ≤3d before expiry","Renewal intent → D2")
p1_in += kpi("in_appopen_post","Input · app open",INPUT,"App-open post-expiry",f"{float(ipp['pct']):.1f}%",
          f"{num(ipp['num'])} of {num(ipp['den'])} open app ≤3d after expiry","Win-back intent")

# Part 1 guardrail — paid-plan status
p1_g = kpi("new_paidstat","Guardrail · base",GOLD,"On paid plan",f"{float(gp_new['pct']):.1f}%",
          f"R0–7 lapsed {float(gp_new['l07']):.1f}% · R7–15 {float(gp_new['l7']):.1f}%","Of day-43-retained (NSM)")

# Part 2 cards — NSM + 2 drivers
p2 = kpi("ten_nsm","NSM · active base · daily",NAVY,"Active-base retention",f"{float(ten['pct']):.1f}%",
         f"{num(ten['num'])} of {num(ten['den'])} active on {fmtd(ten['wk'])} · MTD {float(ten_mtd['pct']):.1f}%","Owner: retention")
p2 += kpi("ten_d1","Driver · renew · daily",TEAL,"On-time renewal",f"{float(td1d['pct']):.1f}%",
          f"{num(td1d['num'])} of {num(td1d['den'])} renewed on time · {fmtd(td1d['wk'])} · 30d {float(td1_30['pct']):.1f}%","Renew by expiry")
p2 += kpi("ten_d2","Driver · recover · daily",TEAL,"Grace recovery",f"{float(td2d['pct']):.1f}%",
          f"{num(td2d['num'])} of {num(td2d['den'])} lapsers win back ≤15d · {fmtd(td2d['wk'])} · 30d {float(td2_30['pct']):.1f}%","Recover before churn")

# Part 2 inputs (tenured-scoped)
p2_in  = kpi("ten_pay","Input · payment",INPUT,"Renewal-payment success",f"{float(tpay['pct']):.1f}%",
          f"{num(tpay['num'])} of {num(tpay['den'])} attempts succeed in 5 min","Mechanical gate → renewal")
p2_in += kpi("ten_appopen","Input · app open",INPUT,"App-open pre-expiry",f"{float(tapp['pct']):.1f}%",
          f"{num(tapp['num'])} of {num(tapp['den'])} open app ≤3d before expiry","Renewal intent")
p2_in += kpi("ten_appopen_post","Input · app open",INPUT,"App-open post-expiry",f"{float(tapp_post['pct']):.1f}%",
          f"{num(tapp_post['num'])} of {num(tapp_post['den'])} open app ≤3d after expiry","Win-back intent")

g_html = f"""<div class="metric" data-k="ten_paidstat" style="--a:{GOLD}" onclick="showTrend('ten_paidstat')">
    <div class="mtier">Guardrail · base</div><div class="mname">On paid plan</div><div class="msub">Of NSM-retained customers</div>
    <div class="mval">{float(gp_ten['pct']):.1f}%</div>
    <div class="mdet">R0–7 lapsed {float(gp_ten['l07']):.1f}% · R7–15 {float(gp_ten['l7']):.1f}%</div><div class="mcue"><span class="cue">trend ↗</span></div></div>
  <div class="metric notrend" style="--a:{GOLD}">
    <div class="mtier">Guardrail</div><div class="mname">% active days</div><div class="msub">Tenured active base</div>
    <div class="mval">{float(gad['avg_pct']):.0f}%</div>
    <div class="mdet">avg coverage · {float(gad['pct']):.1f}% under 30% ({num(gad['num'])})</div><div class="mcue"></div></div>"""

asof = fmtd(D.get("ist_today") or "", 0, '%d %b %Y') if D.get("ist_today") else (D.get("as_of","") or "today")
ser_json = json.dumps(SER)

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Customer POD — J2 renewal health</title>
<style>
 :root{{--ink:#14284a;--sub:#5b6b82;--line:#e3e8f0;--bg:#f4f6fa}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:1120px;margin:0 auto;padding:30px 26px 54px}}
 .top{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid var(--ink);padding-bottom:14px}}
 .eyebrow{{font-size:12px;font-weight:700;letter-spacing:.14em;color:#1f7a70;text-transform:uppercase}}
 h1{{font-size:26px;margin:6px 0 2px}} .h1sub{{color:var(--sub);font-size:13.5px}}
 .asof{{text-align:right;font-size:12px;color:var(--sub);line-height:1.7}} .asof b{{color:var(--ink)}}
 .tabs{{display:flex;gap:8px;margin:20px 0 6px}}
 .tab{{padding:9px 18px;border-radius:9px;font-weight:700;font-size:14px;cursor:pointer;background:#e9edf3;color:var(--sub);border:1px solid transparent}}
 .tab.on{{background:#fff;color:var(--ink);border-color:var(--line);box-shadow:0 1px 2px rgba(20,40,74,.05)}}
 .part{{display:none}} .part.on{{display:block}}
 .owner{{font-size:12px;color:var(--sub);margin:12px 0 10px}}
 .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
 .metric{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 18px 14px;border-top:4px solid var(--a);cursor:pointer;transition:transform .12s,box-shadow .12s}}
 .metric:hover{{transform:translateY(-2px);box-shadow:0 6px 18px rgba(20,40,74,.10)}}
 .metric.notrend{{cursor:default}} .metric.notrend:hover{{transform:none;box-shadow:none}}
 .metric.active{{box-shadow:0 0 0 2px var(--a),0 6px 18px rgba(20,40,74,.12)}}
 .mtier{{font-size:10.5px;font-weight:800;letter-spacing:.09em;color:var(--a);text-transform:uppercase}}
 .mname{{font-size:16px;font-weight:700;margin-top:5px}} .msub{{font-size:11.5px;color:var(--sub)}}
 .mval{{font-size:38px;font-weight:800;letter-spacing:-.03em;margin:8px 0 3px;line-height:1}}
 .mdet{{font-size:12px;color:#374861;min-height:30px}} .mcue{{font-size:10.5px;color:var(--a);margin-top:6px;min-height:14px}}
 .sec{{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--sub);margin:22px 0 10px}}
 .card{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 20px}}
 .bar{{display:flex;align-items:center;gap:12px;margin:9px 0}} .blab{{width:52px;font-weight:700;font-size:14px}}
 .btrk{{flex:1;background:#eef1f6;border-radius:6px;height:22px;overflow:hidden}} .bfill{{height:100%;border-radius:6px}}
 .bval{{width:150px;text-align:right;font-weight:700;font-size:14px}} .bden{{color:var(--sub);font-weight:600;font-size:11px;margin-left:6px}}
 .panel{{background:#fff;border:1px solid var(--line);border-radius:12px;margin-top:14px;overflow:hidden;max-height:0;opacity:0;transition:max-height .3s,opacity .25s}}
 .panel.open{{max-height:500px;opacity:1}} .pinner{{padding:18px 22px}}
 .phead{{display:flex;justify-content:space-between;align-items:baseline}} .ptitle{{font-size:15px;font-weight:700}} .ptitle small{{color:var(--sub);font-weight:600;font-size:12px}}
 .pdelta{{font-size:13px;font-weight:700}} .up{{color:#1f7a70}} .down{{color:#c0392b}}
 .pright{{display:flex;align-items:center;gap:12px}} .pgran{{display:inline-flex;gap:4px}}
 .gbtn{{font-size:10.5px;font-weight:700;padding:3px 10px;border-radius:6px;border:1px solid var(--line);background:#f4f6fa;color:var(--sub);cursor:pointer}}
 .gbtn.on{{background:#14284a;color:#fff;border-color:#14284a}}
 #chart,#chart2{{min-height:236px}} #chart svg,#chart2 svg{{display:block;width:100%;height:236px}}
 .notes{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 20px;font-size:12.5px;color:#374861;line-height:1.6;margin-top:14px}}
 .notes li{{margin:3px 0}} .foot{{margin-top:20px;font-size:11px;color:#93a1b5;text-align:center}}
</style></head><body><div class="wrap">
 <div class="top">
  <div><div class="eyebrow">Customer POD · J2</div><h1>Recharge → Exit renewal health</h1>
   <div class="h1sub">Two journeys: winning the first paid recharge, then keeping the paying base.</div></div>
  <div class="asof">as of <b>{asof}</b>, IST<br>rolling windows<br>base = <b>all Home broadband</b></div>
 </div>

 <div class="tabs"><div class="tab on" data-p="new" onclick="showPart('new')">New customer</div>
   <div class="tab" data-p="ten" onclick="showPart('ten')">Tenured base</div></div>

 <div class="part on" id="part-new">
   <div class="owner">Question: do new customers sign up and survive their first cycle. Owner: activation / onboarding.</div>
   <div class="grid">{p1}</div>
   <div class="panel" id="panel-new"><div class="pinner">
     <div class="phead"><div class="ptitle" id="pt-new"></div>
       <div class="pright"><span class="pgran" id="pg-new"></span><span class="pdelta" id="pd-new"></span></div></div><div id="chart"></div></div></div>
   <div class="sec">Guardrails</div>
   <div class="grid">{p1_g}</div>
   <div class="sec">Inputs — daily levers</div>
   <div class="grid">{p1_in}</div>
 </div>

 <div class="part" id="part-ten">
   <div class="owner">Question: is the paying base staying month over month. Owner: retention.</div>
   <div class="grid">{p2}</div>
   <div class="panel" id="panel-ten"><div class="pinner">
     <div class="phead"><div class="ptitle" id="pt-ten"></div>
       <div class="pright"><span class="pgran" id="pg-ten"></span><span class="pdelta" id="pd-ten"></span></div></div><div id="chart2"></div></div></div>
   <div class="sec">Guardrails</div>
   <div class="grid">{g_html}</div>
   <div class="sec">Inputs — daily levers</div>
   <div class="grid">{p2_in}</div>
 </div>

 <div class="notes">
   <div style="font-weight:700;color:#14284a;margin:2px 0 7px;font-size:13px">Metric definitions</div>
   <ul>
   <li><b>Day-43 retention</b> (new · NSM) — of an install-day cohort, the share still active on day 43. Denominator = all installs. Plotted by day-43 date.</li>
   <li><b>First-paid conversion</b> (new · driver) — of new installs, the share making their first paid recharge within 7 days of free-trial expiry.</li>
   <li><b>Expiry-day renewals</b> (new · driver) — of new-customer paid-plan expiries (all plans blended), the share whose next plan starts on or before expiry.</li>
   <li><b>Renewal-payment success</b> (new · input) — of new-customer renewal-payment checkouts, the share reaching payment success within 5 minutes (attempts deduped per 5-min).</li>
   <li><b>App-open pre-expiry / post-expiry</b> (both · input) — of expiries, the share where the customer opened the app in the 3 days before expiry (pre — renewal intent) or the 3 days after (post — win-back intent; matures 3 days after expiry).</li>
   <li><b>Active-base retention</b> (tenured · NSM) — active tenured customers today ÷ active tenured 30 days ago (rolling 30-day ratio). MTD = of the base active on the 1st, share still active yesterday.</li>
   <li><b>On-time renewal</b> (tenured · driver) — of tenured paid-plan expiries (all plans), the share whose next plan starts on or before expiry.</li>
   <li><b>Grace recovery</b> (tenured · driver) — of tenured expiries that missed on-time renewal, the share who recharge within 15 days (before churning out). Matures 15 days after expiry.</li>
   <li><b>On paid plan</b> (both · guardrail) — decomposes the customers the NSM counts as retained (new: active at day 43; tenured: active today and 30 days ago) by their paid-plan state: on a live paid plan, or lapsed R0–7 / R7–15 days but still inside the 15-day active window. Sums to 100%. Guards against a high NSM that is mostly lapsed-but-not-yet-churned rather than truly paid.</li>
   <li><b>% active days</b> (tenured · guardrail) — average share of days the connection was active over the rolling 30 days.</li>
   </ul>
   <div style="font-weight:700;color:#14284a;margin:12px 0 7px;font-size:13px">Method</div>
   <ul>
   <li>Base = all Home broadband (store_group_id=0), every plan type (PAYG, legacy, migrated). Standard trum filters, IST. Only split is tenure (new &lt;43d / tenured).</li>
   <li>Active = plan live at the checkpoint or last plan ended within 15 days.</li>
   <li>Lagged metrics exclude the current, still-maturing day/cohort. Windows roll on the last 30 days. Charts use a fixed 0–100% axis.</li>
   <li>Refreshed daily from Metabase. Not yet cross-checked against an existing Metabase dashboard.</li>
   </ul>
 </div>
 <div class="foot">Both NSMs toggle daily / weekly. Tenured is a 30-day rolling ratio; its earliest daily points sit on a small base.</div>
</div>
<script>
const SER={ser_json};
const ACC={{new_nsm:'{NAVY}',new_d1:'{TEAL}',new_d2:'{TEAL}',in_pay:'{INPUT}',in_appopen:'{INPUT}',in_appopen_post:'{INPUT}',new_paidstat:'{GOLD}',ten_nsm:'{NAVY}',ten_d1:'{TEAL}',ten_d2:'{TEAL}',ten_pay:'{INPUT}',ten_appopen:'{INPUT}',ten_appopen_post:'{INPUT}',ten_paidstat:'{GOLD}'}};
const GOODDOWN={{}};
const NAME={{new_nsm:'Day-43 retention',new_d1:'First-paid conversion',new_d2:'Expiry-day renewals',in_pay:'Payment success',in_appopen:'App-open pre-expiry',in_appopen_post:'App-open post-expiry',new_paidstat:'On paid plan',ten_nsm:'Active-base retention',ten_d1:'On-time renewal',ten_d2:'Grace recovery',ten_pay:'Renewal-payment success',ten_appopen:'App-open pre-expiry',ten_appopen_post:'App-open post-expiry',ten_paidstat:'On paid plan'}};
const PANEL={{new_nsm:'new',new_d1:'new',new_d2:'new',in_pay:'new',in_appopen:'new',in_appopen_post:'new',new_paidstat:'new',ten_nsm:'ten',ten_d1:'ten',ten_d2:'ten',ten_pay:'ten',ten_appopen:'ten',ten_appopen_post:'ten',ten_paidstat:'ten'}};
const MO=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
let cur={{new:null,ten:null}};
let gran={{new_nsm:'daily',new_d1:'daily',new_d2:'daily',in_pay:'daily',in_appopen:'daily',in_appopen_post:'daily',new_paidstat:'daily',ten_nsm:'daily',ten_d1:'daily',ten_d2:'daily',ten_pay:'daily',ten_appopen:'daily',ten_appopen_post:'daily',ten_paidstat:'daily'}};
function lbl(ds){{return MO[+ds.slice(5,7)-1]+' '+ds.slice(8,10);}}
function addDays(ds,n){{const d=new Date(ds+'T00:00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10);}}
function isoMon(ds){{const d=new Date(ds+'T00:00:00');const wd=(d.getDay()+6)%7;d.setDate(d.getDate()-wd);return d.toISOString().slice(0,10);}}
function getPoints(k){{const s=SER[k];
  const ex=p=>({{l07:p.l07,l7:p.l7}});
  if(s.gran==='weekly'||gran[k]==='daily') return s.points.map(p=>({{x:lbl(p.date),v:p.v,n:p.den,date:p.date,cohort:p.cohort,...ex(p)}}));
  const m={{}};s.points.forEach(p=>{{const w=isoMon(p.date);(m[w]=m[w]||[]).push(p);}});
  return Object.keys(m).sort().map(w=>{{const g=m[w];
    if(g.length<7) return null;   // weekly: only complete (fully-matured) weeks
    if(s.agg==='sum'){{let nu=0,de=0;g.forEach(p=>{{nu+=p.num;de+=p.den;}});return {{x:lbl(w),v:Math.round(nu*1000/de)/10,n:de,date:w}};}}
    const lp=g[g.length-1];return {{x:lbl(lp.date),v:lp.v,n:lp.den,date:lp.date,...ex(lp)}};}}).filter(Boolean);
}}
function showPart(p){{document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on',t.dataset.p===p));
  document.querySelectorAll('.part').forEach(x=>x.classList.toggle('on',x.id==='part-'+p));}}
function showTrend(k){{
  const p=PANEL[k], panel=document.getElementById('panel-'+p);
  document.querySelectorAll('#part-'+p+' .metric').forEach(m=>m.classList.toggle('active',m.dataset.k===k));
  if(cur[p]===k){{panel.classList.remove('open');document.querySelectorAll('#part-'+p+' .metric').forEach(m=>m.classList.remove('active'));cur[p]=null;return;}}
  cur[p]=k;
  document.getElementById('pg-'+p).innerHTML = SER[k].toggle
    ? `<button class='gbtn ${{gran[k]==='daily'?'on':''}}' onclick="setGran('${{k}}','daily')">Daily</button><button class='gbtn ${{gran[k]==='weekly'?'on':''}}' onclick="setGran('${{k}}','weekly')">Weekly</button>` : '';
  render(k); panel.classList.add('open');
}}
function setGran(k,g){{gran[k]=g;const p=PANEL[k];
  document.getElementById('pg-'+p).querySelectorAll('.gbtn').forEach(b=>b.classList.toggle('on',b.textContent.toLowerCase()===g));
  render(k);}}
function render(k){{const p=PANEL[k],s=SER[k],pts=getPoints(k),last=pts[pts.length-1],prev=pts[pts.length-2];
  document.getElementById('pt-'+p).innerHTML=NAME[k]+" <small>· "+(s.toggle?gran[k]:s.gran)+" · "+(s.basis||'')+"</small>";
  const dEl=document.getElementById('pd-'+p);
  if(prev){{const dv=last.v-prev.v,imp=GOODDOWN[k]?(dv<0):(dv>0);dEl.className='pdelta '+(imp?'up':'down');dEl.textContent=(dv>0?'+':'')+dv.toFixed(1)+'pp';}} else dEl.textContent='';
  document.getElementById(p==='new'?'chart':'chart2').innerHTML=chart(s,ACC[k],pts);
}}
function chart(s,acc,pts){{
  const W=1040,H=230,pl=42,pr=130,pt=20,pb=36,iw=W-pl-pr,ih=H-pt-pb;
  let mn=0,mx=100;   // fixed 0–100 y-axis across all charts
  const n=pts.length,X=i=>pl+(n===1?iw/2:iw*i/(n-1)),Y=v=>pt+ih*(1-(v-mn)/(mx-mn));let g='';
  for(let k=0;k<=4;k++){{const val=mn+(mx-mn)*k/4,y=Y(val);g+=`<line x1='${{pl}}' y1='${{y}}' x2='${{pl+iw}}' y2='${{y}}' stroke='#eef1f6'/><text x='${{pl-8}}' y='${{y+3}}' font-size='10' fill='#93a1b5' text-anchor='end'>${{val.toFixed(0)}}%</text>`;}}
  if(s.band){{const y1=Y(s.band[1]),y2=Y(s.band[0]);g+=`<rect x='${{pl}}' y='${{y1}}' width='${{iw}}' height='${{y2-y1}}' fill='#1f7a70' opacity='.06'/>`;}}
  if(s.legacy){{const y=Y(s.legacy);g+=`<line x1='${{pl}}' y1='${{y}}' x2='${{pl+iw}}' y2='${{y}}' stroke='#8a97ab' stroke-width='1.4' stroke-dasharray='5 4'/><text x='${{pl+iw+8}}' y='${{y+3}}' font-size='10.5' fill='#5b6b82'>${{s.legacyLabel}}</text>`;}}
  let d='';pts.forEach((p,i)=>{{d+=(i?'L':'M')+X(i)+' '+Y(p.v)+' ';}});g+=`<path d='${{d}}' fill='none' stroke='${{acc}}' stroke-width='2.2'/>`;
  (s.extra||[]).forEach(e=>{{let dd='';pts.forEach((p,i)=>{{dd+=(i?'L':'M')+X(i)+' '+Y(p[e[0]])+' ';}});
    g+=`<path d='${{dd}}' fill='none' stroke='${{e[2]}}' stroke-width='1.6' stroke-dasharray='4 3'/>`;
    const lp=pts[n-1];g+=`<text x='${{X(n-1)+6}}' y='${{Y(lp[e[0]])+3}}' font-size='9.5' font-weight='700' fill='${{e[2]}}'>${{e[1]}}</text>`;}});
  const step=Math.max(1,Math.ceil(n/9)),rr=n>24?2:3.4;
  pts.forEach((p,i)=>{{const x=X(i),y=Y(p.v),lastp=i===n-1;
    const dlab=p.cohort?('install '+lbl(p.cohort)+' → day-43 '+p.x):(s.eventoff?('cohort '+p.x+' → '+s.eventlbl+' '+lbl(addDays(p.date,s.eventoff))):p.x);
    g+=`<circle cx='${{x}}' cy='${{y}}' r='${{lastp?5:rr}}' fill='${{acc}}'><title>${{dlab}} · ${{p.v}}% · n=${{p.n}}</title></circle>`;
    if(lastp||i===0)g+=`<text x='${{x}}' y='${{y-9}}' font-size='10.5' font-weight='700' fill='${{acc}}' text-anchor='${{lastp?'end':'start'}}'>${{p.v}}%</text>`;
    if(lastp||i%step===0)g+=`<text x='${{x}}' y='${{H-12}}' font-size='9' fill='#93a1b5' text-anchor='middle'>${{p.x}}</text>`;}});
  return `<svg viewBox='0 0 ${{W}} ${{H}}' width='100%'>${{g}}</svg>`;
}}
</script></body></html>"""
open(os.path.join(os.path.dirname(__file__),"index.html"),"w",encoding="utf-8").write(html)
print("wrote index.html")
