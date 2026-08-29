#!/usr/bin/env bash
# 히트맵 전 종목의 기간별 등락과 밸류에이션 배수를 모아 JSON 으로 낸다.
#   fetch_universe.sh <page-handle> <USA|KOR> <출력경로>
set -euo pipefail
B=~/.claude/scripts/browser-driver
PAGE="$1"; MARKET="$2"; OUT="$3"
PERIODS="1d 1w 1m 3m 6m ytd 1y"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# 1. 기간별 등락을 모은다. 종목 식별자는 assetIdentifier 를 쓴다.
for P in $PERIODS; do
  "$B" js "$PAGE" "fetch('/api/financials/market-overview/sector-treemap?period=$P&contentType=$MARKET').then(r=>r.json()).then(j=>{
    const L=[]; const walk=(x,s,g)=>{ if(x.ticker) L.push({id:x.assetIdentifier,t:x.ticker,ex:x.exchange,
      name:(x.shortName&&(x.shortName.ko||x.shortName.en))||x.ticker,cap:x.cap,r:x.rate,s:s,g:g});
      (x.children||[]).forEach(y=>walk(y,s,g)); };
    j.data.forEach(s=>(s.children||[]).forEach(g=>walk(g,s.trbcCode,g.trbcCode)));
    return JSON.stringify(L);
  })" > "$TMP/$P.json"
  printf '  %s %s개\n' "$P" "$(python3 -c "import json,sys;print(len(json.load(open('$TMP/$P.json'))))")" >&2
done

# 2. 종목별 밸류에이션 배수를 배치로 받는다. 접미사는 거래소가 정한다.
python3 -c "
import json
L=json.load(open('$TMP/1d.json'))
sfx={'NASD':'.OQ','NYSE':'.N','KRX':'.KS'}
print('\n'.join(x['t']+sfx.get(x['ex'],'') for x in L))
" > "$TMP/ids.txt"

: > "$TMP/val.jsonl"
BATCH=40; TOTAL=$(wc -l < "$TMP/ids.txt" | tr -d ' ')
for ((i=1; i<=TOTAL; i+=BATCH)); do
  IDS=$(sed -n "${i},$((i+BATCH-1))p" "$TMP/ids.txt" | paste -sd, - | sed 's/[^,]*/"&"/g')
  "$B" js "$PAGE" "Promise.all([$IDS].map(s=>
    fetch('/api/analysis/quote/summary?stockId='+s+'&assetClass=STOCK').then(r=>r.json()).then(j=>{
      const d=(j&&j.data)||{}, sd=d.stockDetailData||{}, v=sd.valuation||[];
      const g=l=>v.find(x=>String(x.label)===l)||{}; const a=g('2026'), b=g('2027');
      const fi=sd.financialInfo||{}, p=sd.price||{}, pe=d.perspectiveData||{};
      if(!sd.price) return {s:s,empty:1};
      return {s:s, mcap:fi.mktCap, ev:fi.evCur, px:p.previousClose,
        per26:a.per, per27:b.per, es26:a.evSales, es27:b.evSales,
        ee26:a.evEbitda, ee27:b.evEbitda, pbr26:a.pbr,
        tgt:pe.mean, nest:pe.numberOfEstimates,
        pr4w:p.pr4w, pr13w:p.pr13w, pr52w:p.pr52w, yr:p.yearRange};
    }).catch(e=>({s:s,err:String(e).slice(0,60)}))
  )).then(a=>JSON.stringify(a))" >> "$TMP/val.jsonl"
  printf '  배수 %d/%d\n' "$((i+BATCH-1<TOTAL?i+BATCH-1:TOTAL))" "$TOTAL" >&2
done

# 3. 합친다
python3 - "$TMP" "$OUT" "$MARKET" <<'PYEOF'
import json, sys, pathlib
tmp, out, market = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
periods = "1d 1w 1m 3m 6m ytd 1y".split()
base = {x["id"]: x for x in json.load(open(tmp / "1d.json"))}
for x in base.values():
    x["ret"] = {}
for p in periods:
    for x in json.load(open(tmp / f"{p}.json")):
        if x["id"] in base:
            base[x["id"]]["ret"][p] = x["r"]
sfx = {"NASD": ".OQ", "NYSE": ".N", "KRX": ".KS"}
val = {}
for line in open(tmp / "val.jsonl"):
    line = line.strip()
    if line:
        for v in json.loads(line):
            val[v["s"]] = v
miss = 0
for x in base.values():
    v = val.get(x["t"] + sfx.get(x["ex"], ""), {})
    if v.get("empty") or v.get("err") or not v:
        miss += 1
    x["val"] = {k: v.get(k) for k in
                ("mcap","ev","per26","per27","es26","es27","ee26","ee27","pbr26","tgt","nest")}
json.dump({"market": market, "count": len(base), "missing_valuation": miss,
           "stocks": list(base.values())}, open(out, "w"), ensure_ascii=False)
print(f"  {out} — {len(base)}개, 배수 결측 {miss}개", file=sys.stderr)
PYEOF
