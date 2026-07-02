# -*- coding: utf-8 -*-
"""Read dashboard_data.json, write index.html — a 2-part dashboard
(Part 1 New customer, Part 2 Tenured base). No hedging copy, terse."""
import json, os
def _lower(o):
    if isinstance(o,list): return [_lower(x) for x in o]
    if isinstance(o,dict): return {k.lower():_lower(v) for k,v in o.items()}
    return o
D = _lower(json.load(open(os.path.join(os.path.dirname(__file__),"dashboard_data.json"))))

NAVY="#14284a"; TEAL="#1f7a70"; GOLD="#c68a1a"; RED="#c0392b"; SUB="#5b6b82"
def num(n):
    try: return "{:,}".format(int(round(float(n))))
    except: return str(n)

MON={'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}
def wk(s):
    return MON.get(s[5:7],s[5:7])+" "+s[8:10] if (isinstance(s,str) and len(s)==10 and s[4]=='-') else str(s)

def series(rows):
    return [{"date":r["wk"],"v":float(r["pct"]),
             "num":int(float(r.get("num",r["den"]))),"den":int(float(r["den"]))} for r in rows]

# ---- assemble the two parts ----
nsm_new = D["new_nsm_headline"]; d1 = D["new_d1_headline"]
d2 = D["new_d2_buckets"]
ten = D["ten_nsm_headline"]; tdrv = D["ten_driver_buckets"]
gad = D["guard_activedays"]; g1d = D["guard_oneday_headline"]

SER = {
 "new_nsm": {"legacy":85,"band":None,"legacyLabel":"Legacy M1 ~85%","gran":"daily","agg":"sum","toggle":True,"points":series(D["new_nsm_daily"])},
 "new_d1":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"weekly","agg":"sum","toggle":False,"points":series(D["new_d1_weekly"])},
 "ten_nsm": {"legacy":90,"band":[85,95],"legacyLabel":"Legacy 85–95%","gran":"daily","agg":"sample","toggle":True,"points":series(D["ten_nsm_daily"])},
 "oneday":  {"legacy":None,"band":None,"legacyLabel":None,"gran":"weekly","agg":"sum","toggle":False,"points":series(D["guard_oneday_weekly"])},
}

def bars(rowset, accent):
    order={"1d":0,"7d":1,"28d":2,"Other":3}
    rws=sorted(rowset,key=lambda r:order.get(r["bucket"],9))
    mx=max(float(r["pct"]) for r in rws) or 1
    h=""
    for r in rws:
        p=float(r["pct"]); w=max(3,p/max(mx,60)*100)
        h+=f"""<div class="bar"><div class="blab">{r['bucket']}</div>
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
p1 = kpi("new_nsm","NSM · Day 43",NAVY,"Day-43 retention",f"{float(nsm_new['pct']):.1f}%",
         f"{num(nsm_new['num'])} of {num(nsm_new['den'])} installs active at day 43","Owner: activation")
p1 += kpi("new_d1","Driver · convert",TEAL,"First-paid conversion",f"{float(d1['pct']):.1f}%",
          f"{num(d1['num'])} of {num(d1['den'])} convert in 7d · {float(d1['same_day']):.0f}% same-day","Leading, ~9-day lag")
p1_d2 = bars(d2, TEAL)

# Part 2 cards
p2 = kpi("ten_nsm","NSM · monthly",NAVY,"Active-base retention",f"{float(ten['pct']):.1f}%",
         f"{num(ten['num'])} of {num(ten['den'])} tenured still active","Owner: retention")
p2_drv = bars(tdrv, NAVY)
g_html = f"""<div class="metric notrend" style="--a:{GOLD}">
    <div class="mtier">Guardrail</div><div class="mname">% active days</div><div class="msub">Tenured active base</div>
    <div class="mval">{float(gad['avg_pct']):.0f}%</div>
    <div class="mdet">avg coverage · {float(gad['pct']):.1f}% under 30% ({num(gad['num'])})</div><div class="mcue"></div></div>
  <div class="metric" data-k="oneday" style="--a:{GOLD}" onclick="showTrend('oneday')">
    <div class="mtier">Guardrail · LTV</div><div class="mname">1-day plan %</div><div class="msub">Lower is better</div>
    <div class="mval">{float(g1d['pct']):.1f}%</div>
    <div class="mdet">{num(g1d['num'])} of {num(g1d['den'])} recharges</div><div class="mcue"><span class="cue">trend ↗</span></div></div>"""

asof = D.get("as_of","") or "today"
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
   <div class="sec">Driver 2 — first-renewal R0, by first-plan bucket</div>
   <div class="card">{p1_d2}</div>
 </div>

 <div class="part" id="part-ten">
   <div class="owner">Question: is the paying base staying month over month. Owner: retention.</div>
   <div class="grid">{p2}{g_html}</div>
   <div class="panel" id="panel-ten"><div class="pinner">
     <div class="phead"><div class="ptitle" id="pt-ten"></div>
       <div class="pright"><span class="pgran" id="pg-ten"></span><span class="pdelta" id="pd-ten"></span></div></div><div id="chart2"></div></div></div>
   <div class="sec">Driver — on-time renewal (R0), by plan bucket</div>
   <div class="card">{p2_drv}</div>
 </div>

 <div class="notes"><ul>
   <li>Base = all Home broadband (store_group_id=0), every plan type (PAYG, legacy, migrated). Standard trum filters, IST. Only split is tenure (new &lt;43d / tenured).</li>
   <li>Active = plan live at the checkpoint or last plan ended within 15 days. New vs tenured split at 43 days from install.</li>
   <li>Day-43 retention counts all installs, so non-converters count against it. Conversion matures ~9 days after install; day-43 lags six weeks and is the confirming outcome.</li>
   <li>First-renewal R0 and on-time R0 read per plan bucket, never blended. Windows roll on the last 30 days / matured cohorts.</li>
   <li>Refreshed daily from Metabase. Not yet cross-checked against an existing Metabase dashboard.</li>
 </ul></div>
 <div class="foot">Both NSMs toggle daily / weekly. Tenured is a 30-day rolling ratio; its earliest daily points sit on a small base.</div>
</div>
<script>
const SER={ser_json};
const ACC={{new_nsm:'{NAVY}',new_d1:'{TEAL}',ten_nsm:'{NAVY}',oneday:'{GOLD}'}};
const GOODDOWN={{oneday:true}};
const NAME={{new_nsm:'Day-43 retention',new_d1:'First-paid conversion',ten_nsm:'Active-base retention',oneday:'1-day plan %'}};
const PANEL={{new_nsm:'new',new_d1:'new',ten_nsm:'ten',oneday:'ten'}};
const MO=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
let cur={{new:null,ten:null}};
let gran={{new_nsm:'daily',new_d1:'weekly',ten_nsm:'daily',oneday:'weekly'}};
function lbl(ds){{return MO[+ds.slice(5,7)-1]+' '+ds.slice(8,10);}}
function isoMon(ds){{const d=new Date(ds+'T00:00:00');const wd=(d.getDay()+6)%7;d.setDate(d.getDate()-wd);return d.toISOString().slice(0,10);}}
function getPoints(k){{const s=SER[k];
  if(s.gran==='weekly'||gran[k]==='daily') return s.points.map(p=>({{x:lbl(p.date),v:p.v,n:p.den}}));
  const m={{}};s.points.forEach(p=>{{const w=isoMon(p.date);(m[w]=m[w]||[]).push(p);}});
  return Object.keys(m).sort().map(w=>{{const g=m[w];
    if(s.agg==='sum'){{let nu=0,de=0;g.forEach(p=>{{nu+=p.num;de+=p.den;}});return {{x:lbl(w),v:Math.round(nu*1000/de)/10,n:de}};}}
    const lp=g[g.length-1];return {{x:lbl(lp.date),v:lp.v,n:lp.den}};}});
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
  document.getElementById('pt-'+p).innerHTML=NAME[k]+" <small>· "+(s.toggle?gran[k]:s.gran)+"</small>";
  const dEl=document.getElementById('pd-'+p);
  if(prev){{const dv=last.v-prev.v,imp=GOODDOWN[k]?(dv<0):(dv>0);dEl.className='pdelta '+(imp?'up':'down');dEl.textContent=(dv>0?'+':'')+dv.toFixed(1)+'pp';}} else dEl.textContent='';
  document.getElementById(p==='new'?'chart':'chart2').innerHTML=chart(s,ACC[k],pts);
}}
function chart(s,acc,pts){{
  const W=1040,H=230,pl=42,pr=130,pt=20,pb=36,iw=W-pl-pr,ih=H-pt-pb;
  const vals=pts.map(p=>p.v).concat(s.legacy?[s.legacy]:[]).concat(s.band||[]);
  let mn=Math.min(...vals),mx=Math.max(...vals);const pad=Math.max(1,(mx-mn)*0.25);mn=Math.floor(mn-pad);mx=Math.ceil(mx+pad);
  const n=pts.length,X=i=>pl+(n===1?iw/2:iw*i/(n-1)),Y=v=>pt+ih*(1-(v-mn)/(mx-mn));let g='';
  for(let k=0;k<=4;k++){{const val=mn+(mx-mn)*k/4,y=Y(val);g+=`<line x1='${{pl}}' y1='${{y}}' x2='${{pl+iw}}' y2='${{y}}' stroke='#eef1f6'/><text x='${{pl-8}}' y='${{y+3}}' font-size='10' fill='#93a1b5' text-anchor='end'>${{val.toFixed(0)}}%</text>`;}}
  if(s.band){{const y1=Y(s.band[1]),y2=Y(s.band[0]);g+=`<rect x='${{pl}}' y='${{y1}}' width='${{iw}}' height='${{y2-y1}}' fill='#1f7a70' opacity='.06'/>`;}}
  if(s.legacy){{const y=Y(s.legacy);g+=`<line x1='${{pl}}' y1='${{y}}' x2='${{pl+iw}}' y2='${{y}}' stroke='#8a97ab' stroke-width='1.4' stroke-dasharray='5 4'/><text x='${{pl+iw+8}}' y='${{y+3}}' font-size='10.5' fill='#5b6b82'>${{s.legacyLabel}}</text>`;}}
  let d='';pts.forEach((p,i)=>{{d+=(i?'L':'M')+X(i)+' '+Y(p.v)+' ';}});g+=`<path d='${{d}}' fill='none' stroke='${{acc}}' stroke-width='2.2'/>`;
  const step=Math.max(1,Math.ceil(n/9)),rr=n>24?2:3.4;
  pts.forEach((p,i)=>{{const x=X(i),y=Y(p.v),lastp=i===n-1;
    g+=`<circle cx='${{x}}' cy='${{y}}' r='${{lastp?5:rr}}' fill='${{acc}}'><title>${{p.x}} · ${{p.v}}% · n=${{p.n}}</title></circle>`;
    if(lastp||i===0)g+=`<text x='${{x}}' y='${{y-9}}' font-size='10.5' font-weight='700' fill='${{acc}}' text-anchor='${{lastp?'end':'start'}}'>${{p.v}}%</text>`;
    if(lastp||i%step===0)g+=`<text x='${{x}}' y='${{H-12}}' font-size='9' fill='#93a1b5' text-anchor='middle'>${{p.x}}</text>`;}});
  return `<svg viewBox='0 0 ${{W}} ${{H}}' width='100%'>${{g}}</svg>`;
}}
</script></body></html>"""
open(os.path.join(os.path.dirname(__file__),"index.html"),"w",encoding="utf-8").write(html)
print("wrote index.html")
