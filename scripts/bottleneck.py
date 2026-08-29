"""섹터 병목 점수. 어느 산업 그룹이 가치사슬의 처리량을 제한하고 있는지 정량 판정한다.

병목이란 수요가 공급을 초과해 그 구간이 전체 처리량을 제한하는 상태다.
병목 구간은 가격결정력을 쥐고 초과이윤을 가져간다. 텐베거는 여기서 나온다.

사용법:
    python3 bottleneck.py reports/universe-USA-20260828.json
    python3 bottleneck.py reports/universe-USA-20260828.json --json
    python3 bottleneck.py reports/universe-USA-20260828.json --group 5710
"""
from __future__ import annotations
import json, sys, math, statistics as st
from pathlib import Path

# ────────────── 병목의 다섯 가지 증거와 가중치 ──────────────
# 가중치는 병목의 정의에서 나온다. 수요가 없으면 병목이 아니고,
# 마진이 안 오르면 공급이 충분하다는 뜻이므로 병목이 아니다.
FACTORS = {
    "demand":     ("수요 초과",   0.30, "매출 성장률. 병목의 1차 증거다"),
    "pricing":    ("가격결정력", 0.25, "이익률 확대. 병목과 단순 성장을 가른다"),
    "capital":    ("자금 집중",   0.20, "시장 대비 초과수익. 시장이 병목을 인지했다는 증거다"),
    "persistence":("지속성",     0.15, "초과수익이 여러 기간에 걸쳐 일관된 정도. 테마와 구조를 가른다"),
    "headroom":   ("미반영 여지", 0.10, "성장 대비 배수가 낮은 정도. 텐베거 여지다"),
}
# 초과수익을 볼 기간과 가중치. 최근일수록 무겁게 둔다.
RETURN_WINDOWS = {"1m": 0.30, "3m": 0.25, "6m": 0.20, "ytd": 0.15, "1y": 0.10}
MIN_MEMBERS = 3          # 종목이 이보다 적은 그룹은 통계가 성립하지 않는다
WINSOR = 0.02            # 이상치가 z 점수를 무너뜨리므로 양끝을 절단한다

SECTOR_NAME = {"50": "에너지", "51": "소재", "52": "산업재", "53": "경기소비재",
               "54": "필수소비재", "55": "금융", "56": "헬스케어", "57": "기술",
               "58": "통신", "59": "유틸리티", "60": "리츠"}


# ────────────── 종목 단위 파생 지표 ──────────────

def derive(x):
    """배수에서 성장률과 마진을 역산한다. 추정이 없으면 None 을 남긴다."""
    v = x["val"]
    d = {}
    es26, es27, ee26, ee27 = v.get("es26"), v.get("es27"), v.get("ee26"), v.get("ee27")
    # 매출 성장률: EV 가 같으므로 EV/Sales 배수의 비율이 매출 비율의 역수가 된다
    d["rev_g"] = es26 / es27 - 1 if es26 and es27 and es27 > 0 else None
    # EBITDA 마진 = (EV/Sales) ÷ (EV/EBITDA)
    m26 = es26 / ee26 if es26 and ee26 and ee26 > 0 else None
    m27 = es27 / ee27 if es27 and ee27 and ee27 > 0 else None
    d["margin26"], d["margin27"] = m26, m27
    d["margin_delta"] = m27 - m26 if m26 is not None and m27 is not None else None
    d["es27"] = es27
    # 성장 대비 배수. 낮을수록 성장이 아직 값에 안 들어갔다
    d["price_of_growth"] = (es27 / (d["rev_g"] * 100)
                            if es27 and d["rev_g"] and d["rev_g"] > 0.02 else None)
    return d


# ────────────── 통계 도구 ──────────────

def wmean(pairs):
    """(값, 가중치) 쌍의 가중평균. 값이 None 인 쌍은 버린다."""
    ps = [(v, w) for v, w in pairs if v is not None and w and w > 0]
    if not ps:
        return None
    tw = sum(w for _, w in ps)
    return sum(v * w for v, w in ps) / tw


def winsorize(xs, p=WINSOR):
    s = sorted(xs)
    if len(s) < 5:
        return list(xs)
    lo, hi = s[int(len(s) * p)], s[int(math.ceil(len(s) * (1 - p))) - 1]
    return [min(max(x, lo), hi) for x in xs]


def zscores(d):
    """{키: 값} 을 z 점수로. 값이 None 인 키는 0 으로 둔다(중립)."""
    keys = [k for k, v in d.items() if v is not None]
    if len(keys) < 2:
        return {k: 0.0 for k in d}
    vals = winsorize([d[k] for k in keys])
    mu = st.fmean(vals)
    sd = st.pstdev(vals) or 1.0
    z = {k: (v - mu) / sd for k, v in zip(keys, vals)}
    return {k: z.get(k, 0.0) for k in d}


# ────────────── 그룹 집계 ──────────────

def aggregate(stocks):
    """산업 그룹 단위로 묶고 팩터 원값을 만든다."""
    groups = {}
    for x in stocks:
        x["d"] = derive(x)
        groups.setdefault(x["g"], []).append(x)

    market_cap = sum(x["cap"] for x in stocks)
    market_ret = {p: wmean([(x["ret"].get(p), x["cap"]) for x in stocks]) or 0.0
                  for p in RETURN_WINDOWS}

    out = {}
    for g, members in groups.items():
        if len(members) < MIN_MEMBERS:
            continue
        cap = sum(m["cap"] for m in members)
        w = lambda f: wmean([(f(m), m["cap"]) for m in members])

        excess = {p: (wmean([(m["ret"].get(p), m["cap"]) for m in members]) or 0.0)
                     - market_ret[p] for p in RETURN_WINDOWS}
        capital = sum(excess[p] * wt for p, wt in RETURN_WINDOWS.items())
        # 지속성: 초과수익이 양수인 기간의 비율을 -1~1 로 옮긴다
        persistence = 2 * sum(1 for v in excess.values() if v > 0) / len(excess) - 1

        pg = w(lambda m: m["d"]["price_of_growth"])
        out[g] = {
            "group": g, "sector": g[:2], "n": len(members), "cap": cap,
            "cap_share": cap / market_cap,
            "raw": {
                "demand": w(lambda m: m["d"]["rev_g"]),
                "pricing": w(lambda m: m["d"]["margin_delta"]),
                "capital": capital,
                "persistence": persistence,
                # 성장 대비 배수는 낮을수록 좋으므로 부호를 뒤집는다
                "headroom": -pg if pg is not None else None,
            },
            "excess": excess,
            "margin27": w(lambda m: m["d"]["margin27"]),
            "es27": w(lambda m: m["d"]["es27"]),
            "price_of_growth": pg,
            "top": sorted(members, key=lambda m: -m["cap"])[:5],
            "members": members,
        }
    return out, market_ret


def score(groups):
    """팩터별 z 점수를 내고 가중합한다."""
    for f in FACTORS:
        z = zscores({g: v["raw"][f] for g, v in groups.items()})
        for g, v in groups.items():
            v.setdefault("z", {})[f] = z[g]
    for v in groups.values():
        v["score"] = sum(v["z"][f] * FACTORS[f][1] for f in FACTORS)
    return groups


# ────────────── 텐베거 후보 ──────────────

MCAP_CEILING = 50_000      # 백만 달러. 10배면 5,000억 달러다
MCAP_SWEET = 10_000        # 이 아래가 10배 여지가 가장 크다


def tenbagger_candidates(group, limit=8):
    """병목 그룹 안에서 10배 여지가 남은 종목을 고른다.

    대형주는 병목의 수혜를 이미 가격에 담았다. 여지는 시총이 작은 쪽에 있다.
    """
    out = []
    for m in group["members"]:
        cap, d = m["val"].get("mcap"), m["d"]
        if not cap or cap > MCAP_CEILING:
            continue
        if d["rev_g"] is None or d["rev_g"] < 0.10:
            continue          # 그룹이 병목이어도 개별 기업이 못 따라가면 제외한다
        size = 1.0 if cap <= MCAP_SWEET else MCAP_SWEET / cap
        out.append({
            "ticker": m["t"], "name": m["name"], "mcap": cap,
            "rev_g": d["rev_g"], "margin_delta": d["margin_delta"],
            "margin27": d["margin27"], "es27": d["es27"],
            "ret_1y": m["ret"].get("1y"), "ret_1m": m["ret"].get("1m"),
            "nest": m["val"].get("nest"), "tgt": m["val"].get("tgt"),
            # 성장을 크게, 마진 확대를 그다음, 작은 시총을 마지막으로 본다
            "rank": d["rev_g"] * 2 + (d["margin_delta"] or 0) * 5 + size,
        })
    return sorted(out, key=lambda x: -x["rank"])[:limit]


# ────────────── 출력 ──────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    data = json.loads(Path(args[0]).read_text())
    groups, market_ret = aggregate(data["stocks"])
    groups = score(groups)
    ranked = sorted(groups.values(), key=lambda v: -v["score"])

    if "--json" in sys.argv:
        for v in ranked:
            v["candidates"] = tenbagger_candidates(v)
            v.pop("members"); v["top"] = [{"t": m["t"], "name": m["name"],
                                           "cap": m["cap"]} for m in v["top"]]
        print(json.dumps({"market": data["market"], "market_ret": market_ret,
                          "factors": {k: {"label": v[0], "weight": v[1], "why": v[2]}
                                      for k, v in FACTORS.items()},
                          "groups": ranked}, ensure_ascii=False, default=float))
        return

    if "--group" in sys.argv:
        g = sys.argv[sys.argv.index("--group") + 1]
        v = groups[g]
        print(f'{g} {SECTOR_NAME.get(v["sector"],"")} — 병목 점수 {v["score"]:+.2f}')
        print(f'  구성 {v["n"]}개, 시총 {v["cap"]/1000:,.0f}십억 달러\n')
        print("  텐베거 후보 (시총 500억 달러 이하, 매출 성장 10% 이상)")
        for c in tenbagger_candidates(v):
            print(f'    {c["ticker"]:6} {c["name"][:22]:24} 시총 {c["mcap"]/1000:7,.1f}십억  '
                  f'성장 {c["rev_g"]*100:5.1f}%  마진변화 '
                  f'{(c["margin_delta"] or 0)*100:+5.1f}%p  1년 {c["ret_1y"] or 0:+6.1f}%')
        return

    print(f'{data["market"]} 시장 산업 그룹 병목 점수  (종목 {data["count"]}개, '
          f'그룹 {len(groups)}개)\n')
    print("팩터와 가중치")
    for k, (label, w, why) in FACTORS.items():
        print(f'  {label:8} {w:4.0%}  {why}')
    print()
    hdr = (f'{"그룹":<6}{"섹터":<8}{"점수":>7}{"수요":>7}{"가격":>7}{"자금":>7}'
           f'{"지속":>7}{"여지":>7}{"성장%":>8}{"마진Δ":>8}{"시총":>10}')
    print(hdr); print("─" * 90)
    for v in ranked[:15]:
        r = v["raw"]
        f = lambda x, s=100: f"{x*s:+.1f}" if x is not None else "   -"
        print(f'{v["group"]:<6}{SECTOR_NAME.get(v["sector"],"?"):<8}{v["score"]:>+7.2f}'
              f'{v["z"]["demand"]:>+7.1f}{v["z"]["pricing"]:>+7.1f}{v["z"]["capital"]:>+7.1f}'
              f'{v["z"]["persistence"]:>+7.1f}{v["z"]["headroom"]:>+7.1f}'
              f'{f(r["demand"]):>8}{f(r["pricing"]):>8}{v["cap"]/1000:>9,.0f}B')
    print("\n하위 3개")
    for v in ranked[-3:]:
        print(f'  {v["group"]} {SECTOR_NAME.get(v["sector"],"?"):8} {v["score"]:+.2f}')

    best = ranked[0]
    print(f'\n── 최상위 병목: {best["group"]} '
          f'{SECTOR_NAME.get(best["sector"],"")} (점수 {best["score"]:+.2f}) ──')
    print(f'  대표 종목 ' + ", ".join(m["t"] for m in best["top"]))
    print(f'  매출 성장 {best["raw"]["demand"]*100:.1f}%  '
          f'마진 변화 {(best["raw"]["pricing"] or 0)*100:+.1f}%p  '
          f'EV/Sales {best["es27"]:.1f}배')
    print(f'  기간별 초과수익  ' + "  ".join(
        f'{p} {best["excess"][p]:+.1f}%' for p in RETURN_WINDOWS))
    cands = tenbagger_candidates(best)
    if cands:
        print(f'\n  텐베거 후보')
        for c in cands[:5]:
            print(f'    {c["ticker"]:6} {c["name"][:20]:22} 시총 {c["mcap"]/1000:6,.1f}십억  '
                  f'성장 {c["rev_g"]*100:5.1f}%  마진변화 {(c["margin_delta"] or 0)*100:+5.1f}%p')
    else:
        print('\n  텐베거 후보 없음 — 이 그룹은 이미 대형주로만 이루어져 있다')


if __name__ == "__main__":
    main()
