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

# ---------- NEW: Day-43 retention (unconditional), weekly + 30d headline ----------
def q_d43(wk):
    grp = "TO_CHAR(DATE_TRUNC('week',install_dt),'YYYY-MM-DD') wk," if wk else "'hdln' wk,"
    lo = f"DATEADD(day,-120,{T})" if wk else f"DATEADD(day,-73,{T})"
    return f"""
WITH base AS (SELECT router_nas_id, transaction_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist,
   ROW_NUMBER() OVER (PARTITION BY router_nas_id ORDER BY otp_issued_time) rn
   FROM t_router_user_mapping WHERE {STD}),
installs AS (SELECT router_nas_id, CAST(start_ist AS DATE) install_dt, DATEADD(day,43,CAST(start_ist AS DATE)) day43
   FROM base WHERE rn=1 AND transaction_id ILIKE '%booking_payment%'
   AND CAST(start_ist AS DATE) BETWEEN {lo} AND DATEADD(day,-43,{T})),
ls AS (SELECT i.router_nas_id, i.install_dt, i.day43,
   MAX(CASE WHEN CAST(b.start_ist AS DATE)<=i.day43 THEN b.end_ist END) last_end
   FROM installs i JOIN base b ON b.router_nas_id=i.router_nas_id GROUP BY 1,2,3)
SELECT {grp} COUNT(*) den,
  SUM(CASE WHEN last_end>=DATEADD(day,-15,day43) THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN last_end>=DATEADD(day,-15,day43) THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM ls GROUP BY 1 ORDER BY 1"""
data["new_nsm_weekly"] = rows(*run(q_d43(True)))
data["new_nsm_headline"] = rows(*run(q_d43(False)))[0]

# ---------- NEW Driver 1: first-paid conversion R7, weekly + 30d headline ----------
def q_conv(wk):
    grp = "TO_CHAR(DATE_TRUNC('week',free_end),'YYYY-MM-DD') wk," if wk else "'hdln' wk,"
    lo = f"DATEADD(day,-90,{T})" if wk else f"DATEADD(day,-37,{T})"
    return f"""
WITH pay AS (SELECT id,price FROM t_plan_configuration WHERE combined_setting_id=22),
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
data["new_d1_weekly"] = rows(*run(q_conv(True)))
data["new_d1_headline"] = rows(*run(q_conv(False)))[0]

# ---------- NEW Driver 2: first-renewal R0 by bucket (first-paid expiry last 30d) ----------
data["new_d2_buckets"] = rows(*run(f"""
WITH pay AS (SELECT id,price,ROUND(time_limit/86400.0) days FROM t_plan_configuration WHERE combined_setting_id=22),
base AS (SELECT router_nas_id, selected_plan_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
paid AS (SELECT b.router_nas_id,b.start_ist,b.end_ist,p.days plan_days,
   ROW_NUMBER() OVER (PARTITION BY b.router_nas_id ORDER BY b.start_ist) rk
   FROM base b JOIN pay p ON b.selected_plan_id=p.id WHERE p.price>0),
firstpaid AS (SELECT router_nas_id,start_ist fp_start,end_ist fp_end,plan_days FROM paid WHERE rk=1),
nextp AS (SELECT f.router_nas_id,f.fp_end,f.plan_days,MIN(b.start_ist) next_start
   FROM firstpaid f JOIN base b ON b.router_nas_id=f.router_nas_id AND b.start_ist>f.fp_start GROUP BY 1,2,3),
j AS (SELECT f.router_nas_id,f.fp_end,f.plan_days,n.next_start
   FROM firstpaid f LEFT JOIN nextp n ON n.router_nas_id=f.router_nas_id)
SELECT CASE WHEN plan_days=1 THEN '1d' WHEN plan_days=7 THEN '7d' WHEN plan_days=28 THEN '28d' ELSE 'Other' END bucket,
  COUNT(*) den,
  SUM(CASE WHEN next_start IS NOT NULL AND CAST(next_start AS DATE)<=CAST(fp_end AS DATE) THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN next_start IS NOT NULL AND CAST(next_start AS DATE)<=CAST(fp_end AS DATE) THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM j WHERE CAST(fp_end AS DATE) BETWEEN DATEADD(day,-30,{T}) AND {T} GROUP BY 1 ORDER BY 1"""))

# ---------- TENURED NSM: active-base retention, rolling 30d; 3 points ----------
def q_mom(back):
    cur=f"DATEADD(day,-{back},{T})"; prev=f"DATEADD(day,-{back+30},{T})"; ten=f"DATEADD(day,-{back+73},{T})"
    return f"""
WITH base AS (SELECT router_nas_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD} AND selected_plan_id IN {PAYPLANS}),
firstrec AS (SELECT router_nas_id, MIN(CAST(start_ist AS DATE)) first_dt FROM base GROUP BY 1),
ap AS (SELECT router_nas_id FROM base GROUP BY 1 HAVING MAX(CASE WHEN CAST(start_ist AS DATE)<={prev} THEN end_ist END) >= DATEADD(day,-15,{prev})),
ac AS (SELECT router_nas_id FROM base GROUP BY 1 HAVING MAX(CASE WHEN CAST(start_ist AS DATE)<={cur} THEN end_ist END) >= DATEADD(day,-15,{cur}))
SELECT TO_CHAR({cur},'YYYY-MM-DD') wk, COUNT(DISTINCT ap.router_nas_id) den, COUNT(DISTINCT ac.router_nas_id) num,
  ROUND(COUNT(DISTINCT ac.router_nas_id)*100.0/NULLIF(COUNT(DISTINCT ap.router_nas_id),0),1) pct
FROM ap JOIN firstrec f ON f.router_nas_id=ap.router_nas_id AND f.first_dt<={ten}
LEFT JOIN ac ON ac.router_nas_id=ap.router_nas_id"""
mom=[]
for back in [60,30,0]:
    mom += rows(*run(q_mom(back)))
data["ten_nsm_series"] = mom
data["ten_nsm_headline"] = mom[-1]

# ---------- TENURED Driver: R0 by bucket (tenured, expiries last 30d) ----------
data["ten_driver_buckets"] = rows(*run(f"""
WITH pay AS (SELECT id,price,ROUND(time_limit/86400.0) days FROM t_plan_configuration WHERE combined_setting_id=22),
base AS (SELECT router_nas_id, selected_plan_id, created_on,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD}),
firstrec AS (SELECT b.router_nas_id, MIN(CAST(b.start_ist AS DATE)) first_dt FROM base b JOIN pay p ON b.selected_plan_id=p.id GROUP BY 1),
seq AS (SELECT b.router_nas_id,b.end_ist,p.days plan_days,p.price,
   LEAD(b.start_ist) OVER (PARTITION BY b.router_nas_id ORDER BY b.start_ist) next_start,
   ROW_NUMBER() OVER (PARTITION BY b.router_nas_id, CAST(b.end_ist AS DATE) ORDER BY b.created_on DESC) dpx
   FROM base b JOIN pay p ON b.selected_plan_id=p.id),
exp AS (SELECT s.plan_days, DATEDIFF('day',s.end_ist,s.next_start) R,
   DATEDIFF('day', f.first_dt, CAST(s.end_ist AS DATE)) tenure
   FROM seq s JOIN firstrec f ON f.router_nas_id=s.router_nas_id
   WHERE s.dpx=1 AND s.price>0 AND CAST(s.end_ist AS DATE) BETWEEN DATEADD(day,-30,{T}) AND {T})
SELECT CASE WHEN plan_days=1 THEN '1d' WHEN plan_days=7 THEN '7d' WHEN plan_days=28 THEN '28d' ELSE 'Other' END bucket,
  COUNT(*) den, SUM(CASE WHEN R IS NOT NULL AND R<=0 THEN 1 ELSE 0 END) num,
  ROUND(SUM(CASE WHEN R IS NOT NULL AND R<=0 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) pct
FROM exp WHERE tenure>43 GROUP BY 1 ORDER BY 1"""))

# ---------- Guardrail: % active days (tenured active base, last 30d) ----------
data["guard_activedays"] = rows(*run(f"""
WITH base AS (SELECT router_nas_id,
   DATEADD(minute,330,otp_issued_time) start_ist, DATEADD(minute,330,otp_expiry_time) end_ist
   FROM t_router_user_mapping WHERE {STD} AND selected_plan_id IN {PAYPLANS}),
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

# ---------- Guardrail: 1-day plan %, weekly + 30d headline ----------
def q_oneday(wk):
    grp="TO_CHAR(DATE_TRUNC('week',TO_DATE(DATEADD(minute,330,t.created_on))),'YYYY-MM-DD') wk," if wk else "'hdln' wk,"
    lo=f"DATEADD(day,-90,{T})" if wk else f"DATEADD(day,-30,{T})"
    return f"""
WITH pay AS (SELECT id,ROUND(time_limit/86400.0) days FROM t_plan_configuration WHERE combined_setting_id=22 AND price>0)
SELECT {grp} COUNT(DISTINCT t.transaction_id) den,
  COUNT(DISTINCT CASE WHEN p.days=1 THEN t.transaction_id END) num,
  ROUND(COUNT(DISTINCT CASE WHEN p.days=1 THEN t.transaction_id END)*100.0/NULLIF(COUNT(DISTINCT t.transaction_id),0),1) pct
FROM t_router_user_mapping t JOIN pay p ON t.selected_plan_id=p.id
WHERE t.otp='DONE' AND t.store_group_id=0 AND t.device_limit>1 AND t.mobile>'5999999999'
  AND t.mobile NOT IN ('6900099267','7679376747')
  AND t.created_by NOT IN (SELECT lco_account_id FROM test_lco_account_id)
  AND TO_DATE(DATEADD(minute,330,t.created_on)) BETWEEN {lo} AND {T}
GROUP BY 1 ORDER BY 1"""
data["guard_oneday_weekly"] = rows(*run(q_oneday(True)))
data["guard_oneday_headline"] = rows(*run(q_oneday(False)))[0]

# stamp (passed in by CI via env; avoids Date.now in restricted contexts)
data["as_of"] = os.environ.get("AS_OF", "")
json.dump(data, open(os.path.join(os.path.dirname(__file__),"dashboard_data.json"),"w"), default=str, indent=1)
print("OK — wrote dashboard_data.json")
for k,v in data.items():
    print(" ", k, "=", (v if isinstance(v,(dict,str)) else f"{len(v)} rows"))
