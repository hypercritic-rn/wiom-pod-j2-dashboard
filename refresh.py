# -*- coding: utf-8 -*-
"""Customer POD J2 — live refresh. Pulls all metrics from Metabase and writes
dashboard_data.json. Windows roll relative to 'today' (IST) so a daily run stays current.
Key: env var METABASE_KEY (CI), else the local Desktop/.env 'Key =' line."""
import json, urllib.request, re, os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_key():
    k = os.environ.get("METABASE_KEY")
    if k: return k.strip()
    p = os.path.expanduser("~/Desktop/.env")
    if not os.path.exists(p): p = r"C:/Users/Rupesh Narayan/Desktop/.env"
    env = open(p, encoding="utf-8", errors="ignore").read()
    m = re.search(r"^\s*Key\s*=\s*'([^']+)'", env, re.M) or re.search(r'^\s*Key\s*=\s*"([^"]+)"', env, re.M)
    return m.group(1).strip()

API_KEY = get_key()
BASE = os.environ.get("METABASE_URL", "https://metabase.wiom.in")
def run(sql):
    body=json.dumps({"database":113,"type":"native","native":{"query":sql}}).encode()
    req=urllib.request.Request(BASE+"/api/dataset",data=body,
        headers={"Content-Type":"application/json","x-api-key":API_KEY})
    d=json.loads(urllib.request.urlopen(req,timeout=400).read())
    data=d.get("data",{})
    if not data.get("cols"): raise RuntimeError(json.dumps(d)[:400])
    return [c["name"] for c in data["cols"]], data["rows"]

STD=("otp='DONE' AND store_group_id=0 AND device_limit>1 AND mobile>'5999999999' "
     "AND mobile NOT IN ('6900099267','7679376747') "
     "AND created_by NOT IN (SELECT lco_account_id FROM test_lco_account_id)")
T="TO_DATE(DATEADD(minute,330,CURRENT_TIMESTAMP()))"                 # today, IST
PAYPLANS="(SELECT id FROM t_plan_configuration WHERE combined_setting_id=22)"

def rows(cols, rws):
    lc=[c.lower() for c in cols]
    return [dict(zip(lc, r)) for r in rws]

data = {}

# IST "today" from the SAME clock as every query (Snowflake CURRENT_TIMESTAMP is UTC → +330 = IST).
# Use this for the displayed "as of" so the label can't drift from the data.
data["ist_today"] = run("SELECT TO_VARCHAR(TO_DATE(DATEADD(minute,330,CURRENT_TIMESTAMP())),'YYYY-MM-DD') d")[1][0][0]

# ---------- NEW: Day-43 retention (unconditional), DAILY install-cohorts + 30d headline ----------
def q_d43(mode):
    hi=f"DATEADD(day,-44,{T})"   # day-43 checkpoint must be fully past (<= yesterday); excludes today's immature cohort
    if mode=="daily":            # plotted by DAY-43 (event) date, last 30 days
        sel="TO_CHAR(day43,'YYYY-MM-DD') wk, TO_CHAR(install_dt,'YYYY-MM-DD') cohort,"; grpby="1,2"; lo=f"DATEADD(day,-73,{T})"
    elif mode=="mtd":                                                             # day-43 checkpoint this month, through yesterday
        sel="'mtd' wk, NULL cohort,"; grpby="1"; lo=f"DATEADD(day,-43,DATE_TRUNC('month',{T}))"
    else:
        sel="'hdln' wk, NULL cohort,"; grpby="1"; lo=f"DATEADD(day,-73,{T})"      # 30d aggregate
    return f"""
WITH base AS (SELECT router_nas_id, transaction_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist,
   ROW_NUMBER() OVER (PARTITION BY router_nas_id ORDER BY otp_issued_time) rn
   FROM t_router_user_mapping WHERE {STD}),
installs AS (SELECT router_nas_id, CAST(start_ist AS DATE) install_dt, DATEADD(day,43,CAST(start_ist AS DATE)) day43
   FROM base WHERE rn=1 AND transaction_id ILIKE '%booking_payment%'
   AND CAST(start_ist AS DATE) BETWEEN {lo} AND {hi}),
ls AS (SELECT i.router_nas_id, i.install_dt, i.day43,
   MAX(CASE WHEN CAST(b.start_ist AS DATE)<=i.day43 THEN b.end_ist END) last_end
   FROM installs i JOIN base b ON b.router_nas_id=i.router_nas_id GROUP BY 1,2,3)
SELECT {sel} COUNT(*) den,
  SUM(CASE WHEN last_end>=DATEADD(day,-15,day43) THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN last_end>=DATEADD(day,-15,day43) THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM ls GROUP BY {grpby} ORDER BY 1"""
data["new_nsm_daily"] = rows(*run(q_d43("daily")))
data["new_nsm_headline"] = rows(*run(q_d43("headline")))[0]
data["new_nsm_mtd"] = rows(*run(q_d43("mtd")))[0]

# ---------- NEW Driver 1: first-paid conversion R7, weekly + 30d headline ----------
def q_conv(mode):   # daily = by free-trial-expiry day (last 90d, matured); headline = 30d aggregate
    grp = "TO_CHAR(CAST(free_end AS DATE),'YYYY-MM-DD') wk," if mode=="daily" else "'hdln' wk,"
    lo = f"DATEADD(day,-97,{T})" if mode=="daily" else f"DATEADD(day,-37,{T})"
    return f"""
WITH pay AS (SELECT id,price FROM t_plan_configuration),
base AS (SELECT router_nas_id, transaction_id, selected_plan_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist,
   ROW_NUMBER() OVER (PARTITION BY router_nas_id ORDER BY otp_issued_time) rn
   FROM t_router_user_mapping WHERE {STD}),
fp AS (SELECT b.router_nas_id, MIN(b.start_ist) fp FROM base b JOIN pay p ON b.selected_plan_id=p.id WHERE p.price>0 GROUP BY 1),
free AS (SELECT b.router_nas_id, b.end_ist free_end, DATEDIFF('day', b.end_ist, fp.fp) R
   FROM base b LEFT JOIN fp ON fp.router_nas_id=b.router_nas_id
   WHERE b.rn=1 AND b.transaction_id ILIKE '%booking_payment%'
   AND CAST(b.end_ist AS DATE) BETWEEN {lo} AND DATEADD(day,-7,{T}))
SELECT {grp} COUNT(*) den,
  SUM(CASE WHEN R IS NOT NULL AND R BETWEEN 0 AND 7 THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN R IS NOT NULL AND R BETWEEN 0 AND 7 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) pct,
  ROUND(SUM(CASE WHEN R IS NOT NULL AND R<=0 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) same_day
FROM free GROUP BY 1 ORDER BY 1"""
data["new_d1_daily"] = rows(*run(q_conv("daily")))
data["new_d1_headline"] = rows(*run(q_conv("headline")))[0]

# ---------- NEW Driver 2: Expiry-day renewals (renewal rate) — new-customer paid expiries ----------
def q_newrenew(mode, ten=False):   # ALL plans blended, on-time renewal (R0), by expiry day, last 30 days (exclude today = incomplete)
    lo=f"DATEADD(day,-30,{T})"; hi=f"DATEADD(day,-1,{T})"; extra="tenure>43" if ten else "tenure<=43"
    sel="TO_CHAR(CAST(end_ist AS DATE),'YYYY-MM-DD') wk," if mode=="daily" else "'hdln' wk,"
    return f"""
WITH pay AS (SELECT id,price,ROUND(time_limit/86400.0) days FROM t_plan_configuration),
base AS (SELECT router_nas_id, selected_plan_id, created_on,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
fr AS (SELECT b.router_nas_id, MIN(CAST(b.start_ist AS DATE)) first_dt FROM base b JOIN pay p ON b.selected_plan_id=p.id GROUP BY 1),
seq AS (SELECT b.router_nas_id, b.end_ist, p.days plan_days, p.price,
   LEAD(b.start_ist) OVER (PARTITION BY b.router_nas_id ORDER BY b.start_ist) nxt,
   ROW_NUMBER() OVER (PARTITION BY b.router_nas_id, CAST(b.end_ist AS DATE) ORDER BY b.created_on DESC) dpx
   FROM base b JOIN pay p ON b.selected_plan_id=p.id),
exp AS (SELECT s.end_ist, s.plan_days, DATEDIFF('day',s.end_ist,s.nxt) R,
   DATEDIFF('day', f.first_dt, CAST(s.end_ist AS DATE)) tenure
   FROM seq s JOIN fr f ON f.router_nas_id=s.router_nas_id
   WHERE s.dpx=1 AND s.price>0 AND CAST(s.end_ist AS DATE) BETWEEN {lo} AND {hi})
SELECT {sel} COUNT(*) den, SUM(CASE WHEN R IS NOT NULL AND R<=0 THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN R IS NOT NULL AND R<=0 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM exp WHERE {extra} GROUP BY 1 ORDER BY 1"""
data["new_d2_daily"]    = rows(*run(q_newrenew("daily")))
data["new_d2_headline"] = rows(*run(q_newrenew("headline")))[0]
data["ten_d1_daily"]    = rows(*run(q_newrenew("daily", ten=True)))
data["ten_d1_headline"] = rows(*run(q_newrenew("headline", ten=True)))[0]

# ---------- TENURED Driver 2: grace recovery — of missed-on-time expiries, share recharging within 15d (matured: expiry<=today-15) ----------
def q_recovery(mode):
    lo=f"DATEADD(day,-45,{T})"; hi=f"DATEADD(day,-15,{T})"
    sel="TO_CHAR(CAST(end_ist AS DATE),'YYYY-MM-DD') wk," if mode=="daily" else "'hdln' wk,"
    return f"""
WITH pay AS (SELECT id,price FROM t_plan_configuration),
base AS (SELECT router_nas_id, selected_plan_id, created_on,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
fr AS (SELECT b.router_nas_id, MIN(CAST(b.start_ist AS DATE)) first_dt FROM base b JOIN pay p ON b.selected_plan_id=p.id GROUP BY 1),
seq AS (SELECT b.router_nas_id, b.end_ist, p.price,
   LEAD(b.start_ist) OVER (PARTITION BY b.router_nas_id ORDER BY b.start_ist) nxt,
   ROW_NUMBER() OVER (PARTITION BY b.router_nas_id, CAST(b.end_ist AS DATE) ORDER BY b.created_on DESC) dpx
   FROM base b JOIN pay p ON b.selected_plan_id=p.id),
exp AS (SELECT s.end_ist, DATEDIFF('day',s.end_ist,s.nxt) R, DATEDIFF('day', f.first_dt, CAST(s.end_ist AS DATE)) tenure
   FROM seq s JOIN fr f ON f.router_nas_id=s.router_nas_id
   WHERE s.dpx=1 AND s.price>0 AND CAST(s.end_ist AS DATE) BETWEEN {lo} AND {hi})
SELECT {sel}
  SUM(CASE WHEN R IS NULL OR R>0 THEN 1 ELSE 0 END) den,
  SUM(CASE WHEN R BETWEEN 1 AND 15 THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN R BETWEEN 1 AND 15 THEN 1 ELSE 0 END)*100.0/NULLIF(SUM(CASE WHEN R IS NULL OR R>0 THEN 1 ELSE 0 END),0),1) pct
FROM exp WHERE tenure>43 GROUP BY 1 ORDER BY 1"""
data["ten_d2_daily"]    = rows(*run(q_recovery("daily")))
data["ten_d2_headline"] = rows(*run(q_recovery("headline")))[0]

# ---------- NEW INPUTS: payment success, nudge ----------
def q_pay(mode, ten=False):  # renewal-payment 5-min funnel; daily by checkout day, last 30 days (exclude today = partial)
    grp="TO_CHAR(CAST(ts0 AS DATE),'YYYY-MM-DD') wk," if mode=="daily" else "'hdln' wk,"
    lo=f"DATEADD(day,-30,{T})"; hi=f"DATEADD(day,-1,{T})"
    tclause="DATEDIFF('day',fr.first_dt,e.ed) > 43" if ten else "DATEDIFF('day',fr.first_dt,e.ed) BETWEEN 0 AND 43"
    return f"""
WITH fr AS (SELECT router_nas_id, MIN(CAST(DATEADD(minute,330,otp_issued_time) AS DATE)) first_dt FROM t_router_user_mapping WHERE {STD} GROUP BY 1),
ev AS (SELECT TRY_TO_NUMBER(NASID_LONG) nas, TRY_TO_TIMESTAMP(TIMESTAMP) ts, EVENT_NAME en, TO_DATE(TIMESTAMP) ed
   FROM public.CT_CUSTOMER_PAYG_PAYMENT_EVENTS_MV
   WHERE FUNNEL_STEP ILIKE '%renew%' AND TO_DATE(TIMESTAMP) BETWEEN {lo} AND {hi}),
evn AS (SELECT e.nas,e.ts,e.en FROM ev e JOIN fr ON fr.router_nas_id=e.nas WHERE {tclause}),
att AS (SELECT nas, MIN(ts) ts0 FROM evn WHERE en='checkout_page_loaded' GROUP BY nas, FLOOR(DATE_PART(epoch_second,ts)/300)),
succ AS (SELECT DISTINCT nas, ts FROM evn WHERE en='payment_success_page_loaded'),
conv AS (SELECT a.nas, a.ts0,
   CASE WHEN EXISTS (SELECT 1 FROM succ s WHERE s.nas=a.nas AND s.ts BETWEEN a.ts0 AND DATEADD(minute,5,a.ts0)) THEN 1 ELSE 0 END c
   FROM att a)
SELECT {grp} COUNT(*) den, SUM(c) num, ROUND(SUM(c)*100.0/NULLIF(COUNT(*),0),1) pct FROM conv GROUP BY 1 ORDER BY 1"""
data["in_pay_daily"]=rows(*run(q_pay("daily")))
data["in_pay_headline"]=rows(*run(q_pay("headline")))[0]
data["ten_pay_daily"]=rows(*run(q_pay("daily", ten=True)))
data["ten_pay_headline"]=rows(*run(q_pay("headline", ten=True)))[0]

def q_appopen(mode, ten=False, post=False):  # app open near expiry; pre = 3d before, post = 3d after (matured)
    grp="TO_CHAR(exp_dt,'YYYY-MM-DD') wk," if mode=="daily" else "'hdln' wk,"
    if post:
        lo=f"DATEADD(day,-33,{T})"; hi=f"DATEADD(day,-4,{T})"; win="o.d BETWEEN DATEADD(day,1,e.exp_dt) AND DATEADD(day,3,e.exp_dt)"
    else:
        lo=f"DATEADD(day,-30,{T})"; hi=f"DATEADD(day,-1,{T})"; win="o.d BETWEEN DATEADD(day,-3,e.exp_dt) AND e.exp_dt"
    tclause="> 43" if ten else "<=43"
    return f"""
WITH pay AS (SELECT id,price FROM t_plan_configuration),
base AS (SELECT router_nas_id, selected_plan_id, created_on,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
fr AS (SELECT b.router_nas_id, MIN(CAST(b.start_ist AS DATE)) first_dt FROM base b JOIN pay p ON b.selected_plan_id=p.id GROUP BY 1),
seq AS (SELECT b.router_nas_id, b.end_ist, p.price,
   ROW_NUMBER() OVER (PARTITION BY b.router_nas_id, CAST(b.end_ist AS DATE) ORDER BY b.created_on DESC) dpx
   FROM base b JOIN pay p ON b.selected_plan_id=p.id),
enew AS (SELECT s.router_nas_id, CAST(s.end_ist AS DATE) exp_dt FROM seq s JOIN fr f ON f.router_nas_id=s.router_nas_id
   WHERE s.dpx=1 AND s.price>0 AND CAST(s.end_ist AS DATE) BETWEEN {lo} AND {hi} AND DATEDIFF('day',f.first_dt,CAST(s.end_ist AS DATE)) {tclause}),
opens AS (SELECT DISTINCT TRY_TO_NUMBER(NASIDLONG) nas, TO_DATE(TIMESTAMP) d FROM public.CT_CUSTOMER_APP_LAUNCH
   WHERE TO_DATE(TIMESTAMP) BETWEEN DATEADD(day,-37,{T}) AND {T}),
ew AS (SELECT e.router_nas_id, e.exp_dt, MAX(CASE WHEN o.nas IS NOT NULL THEN 1 ELSE 0 END) opened
   FROM enew e LEFT JOIN opens o ON o.nas=e.router_nas_id AND {win} GROUP BY 1,2)
SELECT {grp} COUNT(*) den, SUM(opened) num, ROUND(SUM(opened)*100.0/COUNT(*),1) pct FROM ew GROUP BY 1 ORDER BY 1"""
data["in_appopen_daily"]=rows(*run(q_appopen("daily")))
data["in_appopen_headline"]=rows(*run(q_appopen("headline")))[0]
data["in_appopen_post_daily"]=rows(*run(q_appopen("daily", post=True)))
data["in_appopen_post_headline"]=rows(*run(q_appopen("headline", post=True)))[0]
data["ten_appopen_daily"]=rows(*run(q_appopen("daily", ten=True)))
data["ten_appopen_headline"]=rows(*run(q_appopen("headline", ten=True)))[0]
data["ten_appopen_post_daily"]=rows(*run(q_appopen("daily", ten=True, post=True)))
data["ten_appopen_post_headline"]=rows(*run(q_appopen("headline", ten=True, post=True)))[0]

# ---------- TENURED NSM: active-base retention, rolling 30d, DAILY series ----------
# For each report day D: active(D) / active(D-30), tenured (first_dt <= D-30-43).
# A customer is active on day d if some plan covers [start, expiry+15] on d.
data["ten_nsm_daily"] = rows(*run(f"""
WITH base AS (SELECT router_nas_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
firstrec AS (SELECT router_nas_id, MIN(CAST(start_ist AS DATE)) first_dt FROM base GROUP BY 1),
spine AS (SELECT DATEADD(day, SEQ4(), DATEADD(day,-90,{T})) d FROM TABLE(GENERATOR(ROWCOUNT=>91))),
act AS (SELECT DISTINCT b.router_nas_id, s.d, f.first_dt
   FROM base b JOIN firstrec f ON f.router_nas_id=b.router_nas_id
   JOIN spine s ON s.d BETWEEN CAST(b.start_ist AS DATE) AND DATEADD(day,15,CAST(b.end_ist AS DATE)))
SELECT TO_CHAR(DATEADD(day,30,a.d),'YYYY-MM-DD') wk,
   COUNT(DISTINCT a.router_nas_id) den,
   COUNT(DISTINCT CASE WHEN b.router_nas_id IS NOT NULL THEN a.router_nas_id END) num,
   ROUND(COUNT(DISTINCT CASE WHEN b.router_nas_id IS NOT NULL THEN a.router_nas_id END)*100.0
         /NULLIF(COUNT(DISTINCT a.router_nas_id),0),1) pct
FROM act a
LEFT JOIN act b ON b.router_nas_id=a.router_nas_id AND b.d=DATEADD(day,30,a.d)
WHERE DATEADD(day,30,a.d) BETWEEN DATEADD(day,-30,{T}) AND DATEADD(day,-1,{T})
  AND a.first_dt <= DATEADD(day,-43,a.d)
GROUP BY 1 ORDER BY 1"""))
data["ten_nsm_headline"] = data["ten_nsm_daily"][-1]

# Tenured NSM month-to-date: of tenured active on the 1st, share still active yesterday
data["ten_nsm_mtd"] = rows(*run(f"""
WITH base AS (SELECT router_nas_id, DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist FROM t_router_user_mapping WHERE {STD}),
fr AS (SELECT router_nas_id, MIN(CAST(start_ist AS DATE)) first_dt FROM base GROUP BY 1),
cust AS (SELECT b.router_nas_id, MIN(f.first_dt) first_dt,
   MAX(CASE WHEN CAST(b.start_ist AS DATE)<=DATE_TRUNC('month',{T}) THEN CAST(b.end_ist AS DATE) END) exp_m0,
   MAX(CASE WHEN CAST(b.start_ist AS DATE)<=DATEADD(day,-1,{T}) THEN CAST(b.end_ist AS DATE) END) exp_y
   FROM base b JOIN fr f ON f.router_nas_id=b.router_nas_id GROUP BY 1)
SELECT 'mtd' wk, COUNT(*) den,
  SUM(CASE WHEN exp_y >= DATEADD(day,-16,{T}) THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN exp_y >= DATEADD(day,-16,{T}) THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) pct
FROM cust
WHERE first_dt <= DATEADD(day,-43,DATE_TRUNC('month',{T}))
  AND exp_m0 >= DATEADD(day,-15,DATE_TRUNC('month',{T}))"""))[0]

# ---------- Guardrail: % active days (tenured active base, last 30d) ----------
data["guard_activedays"] = rows(*run(f"""
WITH base AS (SELECT router_nas_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
firstrec AS (SELECT router_nas_id, MIN(CAST(start_ist AS DATE)) first_dt FROM base GROUP BY 1),
ta AS (SELECT b.router_nas_id FROM base b JOIN firstrec f ON f.router_nas_id=b.router_nas_id
   WHERE f.first_dt<=DATEADD(day,-43,{T})
   GROUP BY 1 HAVING MAX(CASE WHEN CAST(b.start_ist AS DATE)<={T} THEN b.end_ist END) >= DATEADD(day,-15,{T})),
days AS (SELECT DATEADD(day, SEQ4(), DATEADD(day,-30,{T})) d FROM TABLE(GENERATOR(ROWCOUNT=>30))),
cov AS (SELECT t.router_nas_id, COUNT(DISTINCT d.d) ad
   FROM ta t LEFT JOIN base b ON b.router_nas_id=t.router_nas_id
   LEFT JOIN days d ON d.d BETWEEN CAST(b.start_ist AS DATE) AND CAST(b.end_ist AS DATE) GROUP BY 1)
SELECT COUNT(*) den, ROUND(AVG(ad)/30.0*100,1) avg_pct,
  SUM(CASE WHEN ad<9 THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN ad<9 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM cov"""))[0]

# ---------- Guardrail: paid-plan status snapshot per day (both cohorts) ----------
# Base = the NSM active base (paid plan live, or lapsed <=15d). Split: on paid plan / lapsed R0-7 / lapsed R7-15.
def q_paidstat(ten):
    tclause = "install_dt <= DATEADD(day,-43,d)" if ten else "install_dt > DATEADD(day,-43,d)"
    return f"""
WITH pay AS (SELECT id,price FROM t_plan_configuration),
allrec AS (SELECT router_nas_id, CAST(DATEADD(minute,330,otp_issued_time) AS DATE) sd, CAST(DATEADD(minute,330,otp_expiry_time) AS DATE) ed, p.price
   FROM t_router_user_mapping t JOIN pay p ON t.selected_plan_id=p.id WHERE {STD}),
inst AS (SELECT router_nas_id, MIN(sd) install_dt FROM allrec GROUP BY 1),
base AS (SELECT * FROM allrec WHERE ed >= DATEADD(day,-60,{T})),
spine AS (SELECT DATEADD(day, SEQ4(), DATEADD(day,-30,{T})) d FROM TABLE(GENERATOR(ROWCOUNT=>30))),
cd AS (SELECT s.d, b.router_nas_id, i.install_dt, MAX(CASE WHEN b.sd<=s.d AND b.price>0 THEN b.ed END) latest_exp
   FROM spine s JOIN base b ON b.sd<=s.d JOIN inst i ON i.router_nas_id=b.router_nas_id GROUP BY s.d, b.router_nas_id, i.install_dt),
stat AS (SELECT d, install_dt, CASE WHEN latest_exp>=d THEN 'paid' WHEN latest_exp>=DATEADD(day,-7,d) THEN 'l07' WHEN latest_exp>=DATEADD(day,-15,d) THEN 'l7' END st
   FROM cd WHERE latest_exp IS NOT NULL)
SELECT TO_CHAR(d,'YYYY-MM-DD') wk, COUNT(*) den, SUM(CASE WHEN st='paid' THEN 1 ELSE 0 END) num,
   ROUND(SUM(CASE WHEN st='paid' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct,
   ROUND(SUM(CASE WHEN st='l07' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) l07,
   ROUND(SUM(CASE WHEN st='l7' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) l7
FROM stat WHERE st IS NOT NULL AND {tclause} GROUP BY 1 ORDER BY 1"""
data["new_paidstat_daily"] = rows(*run(q_paidstat(False)))
data["ten_paidstat_daily"] = rows(*run(q_paidstat(True)))

# stamp (passed in by CI via env; avoids Date.now in restricted contexts)
data["as_of"] = os.environ.get("AS_OF", "")
json.dump(data, open(os.path.join(os.path.dirname(__file__),"dashboard_data.json"),"w"), default=str, indent=1)
print("OK — wrote dashboard_data.json")
for k,v in data.items():
    print(" ", k, "=", (v if isinstance(v,(dict,str)) else f"{len(v)} rows"))
