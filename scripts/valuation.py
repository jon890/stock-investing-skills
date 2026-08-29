"""종목 무관 밸류에이션 엔진. 종목별 가정은 inputs/<TICKER>.json 이 담는다.

사용법:
    python3 valuation.py MRVL              전체 실행
    python3 valuation.py MRVL --json       결과를 JSON 으로 (리포트 생성용)
"""
from __future__ import annotations
import json, sys, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"


# ────────────────────────────── 공통 도구 ──────────────────────────────

def bisect(f, lo, hi, tol=1e-9):
    """f 의 증감 방향을 양 끝에서 판정하고 근을 찾는다.

    방향을 가정하면 구간 끝값이 답으로 나와도 알아채지 못한다 (실측).
    """
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError(f"구간 [{lo}, {hi}] 안에 근이 없다 (f={flo:.4g}, {fhi:.4g})")
    for _ in range(300):
        mid = (lo + hi) / 2
        if f(mid) * flo > 0:
            lo, flo = mid, f(mid)
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def linfit(xs, ys):
    """단순 회귀. 결정계수와 계수를 낸다."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    b1 = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sxx
    b0 = my - b1 * mx
    syy = sum((b - my) ** 2 for b in ys)
    ss = sum((b - (b0 + b1 * a)) ** 2 for a, b in zip(xs, ys))
    return {"r2": 1 - ss / syy, "b0": b0, "b1": b1,
            "xmin": min(xs), "xmax": max(xs), "n": n}


def ramp(a, b, n):
    """a 에서 b 까지 n 개 값을 선형으로 잇는다."""
    return [a] if n == 1 else [a + (b - a) * i / (n - 1) for i in range(n)]


# ────────────────────────────── DCF ──────────────────────────────

def project_revenue(explicit, tail_growth):
    rev = list(explicit)
    for g in tail_growth:
        rev.append(rev[-1] * (1 + g))
    return rev


def dcf(rev, opm, sbc_pct, tax, nwc_pct, wacc, g, last_actual_rev):
    """FCF = 매출 × 영업이익률 × (1−세율) − SBC − 운전자본 증가분.

    감가상각과 설비투자는 상쇄로 둔다. 팹리스가 아니면 inputs 에서 capex_pct 를 준다.
    SBC 는 주주의 실질 비용이므로 반드시 차감한다.
    """
    prev, fcfs, rows = last_actual_rev, [], []
    for r, m, s in zip(rev, opm, sbc_pct):
        nopat = r * m * (1 - tax)
        sbc, dnwc = r * s, (r - prev) * nwc_pct
        fcf = nopat - sbc - dnwc
        fcfs.append(fcf)
        rows.append({"rev": r, "opm": m, "nopat": nopat, "sbc": sbc,
                     "dnwc": dnwc, "fcf": fcf})
        prev = r
    pv = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(fcfs))
    pv_tv = fcfs[-1] * (1 + g) / (wacc - g) / (1 + wacc) ** len(fcfs)
    ev = pv + pv_tv
    return {"rows": rows, "pv": pv, "pv_tv": pv_tv, "ev": ev,
            "tv_share": pv_tv / ev}


def per_share(ev, shares, net_debt):
    return (ev - net_debt) / shares


def run_scenarios(cfg):
    m, out, weighted, psum = cfg["market"], {}, 0.0, 0.0
    for name, s in cfg["scenarios"].items():
        rev = project_revenue(s["revenue"], s["tail_growth"])
        n = len(rev)
        opm = s["opm"] + [s["opm"][-1]] * (n - len(s["opm"]))
        sbc = s["sbc_pct"] if isinstance(s["sbc_pct"], list) else [s["sbc_pct"]] * n
        sbc = sbc + [sbc[-1]] * (n - len(sbc))
        r = dcf(rev, opm, sbc, s["tax"], s["nwc_pct"], s["wacc"], s["g"],
                cfg["fundamentals"]["last_actual_revenue"])
        r["ps"] = per_share(r["ev"], m["shares"], m["net_debt"])
        r["p"] = s["probability"]
        r["upside"] = r["ps"] / m["price"] - 1
        out[name] = r
        weighted += s["probability"] * r["ps"]
        psum += s["probability"]
    if abs(psum - 1.0) > 1e-6:
        raise ValueError(f"시나리오 확률 합이 {psum:.3f} 이다. 1.0 이어야 한다.")
    return out, weighted


# ────────────────────────────── 역DCF ──────────────────────────────

def reverse_dcf(cfg, base_name="기본"):
    m, f = cfg["market"], cfg["fundamentals"]
    s = cfg["scenarios"][base_name]
    target_ev = m["price"] * m["shares"] + m["net_debt"]
    rev = project_revenue(s["revenue"], s["tail_growth"])
    n = len(rev)
    opm = s["opm"] + [s["opm"][-1]] * (n - len(s["opm"]))
    sbc = s["sbc_pct"] if isinstance(s["sbc_pct"], list) else [s["sbc_pct"]] * n
    sbc = sbc + [sbc[-1]] * (n - len(sbc))
    last = f["last_actual_revenue"]

    def ev_of(**kw):
        return dcf(kw.get("rev", rev), kw.get("opm", opm), sbc, s["tax"],
                   s["nwc_pct"], kw.get("wacc", s["wacc"]), kw.get("g", s["g"]),
                   last)["ev"]

    res = {"target_ev": target_ev}
    # 할인율은 영구성장률보다 커야 잔존가치가 발산하지 않는다
    res["implied_wacc"] = bisect(lambda w: target_ev - ev_of(wacc=w), s["g"] + 0.005, 0.40)
    k = bisect(lambda k: target_ev - ev_of(rev=[r * k for r in rev]), 0.2, 20.0)
    res["revenue_multiple"] = k
    res["implied_terminal_revenue"] = rev[-1] * k
    res["implied_cagr"] = (rev[-1] * k / last) ** (1 / n) - 1
    res["implied_g"] = bisect(lambda g: target_ev - ev_of(g=g), -0.20, s["wacc"] - 1e-4)
    res["implied_opm"] = bisect(lambda x: target_ev - ev_of(opm=[x] * n), 0.01, 0.95)
    res["years"] = n
    return res


# ────────────────────────────── 상대가치 ──────────────────────────────

MULTIPLE_CAVEATS = {
    "per_ltm": "인수 무형자산 상각이 GAAP 순이익을 눌러 값이 왜곡된다",
    "pbr": "인수 이력이 많거나 자산이 가벼운 기업은 장부가가 의미를 잃는다",
    "ev_sales": "마진 차이를 보지 못한다. 마진 격차가 큰 비교군에서는 단독으로 쓰지 않는다",
    "ev_ebitda": "자본구조와 상각 정책 차이를 지운다. 장치 산업의 기본 배수다",
}


def prep_peers(peers, ev_field="ev", target=None):
    """배수에서 매출과 EBITDA 를 역산하고 성장률을 붙인다."""
    for x in peers.values():
        ev = x.get(ev_field)
        x["sales_f2"] = ev / x["es27"] if x.get("es27") else None
        x["ebitda_f2"] = ev / x["ee27"] if x.get("ee27") else None
        x["rev_g"] = x["es26"] / x["es27"] - 1 if x.get("es27") and x.get("es26") else None
        x["eps_g"] = x["per26"] / x["per27"] - 1 if x.get("per27") and x.get("per26") else None
    return peers


def consensus_check(peer, guidance_sales):
    """컨센서스가 회사 가이던스를 반영했는지 본다. 실적 발표 직후에는 거의 늘 어긋난다."""
    est = peer["sales_f2"]
    gap = est / guidance_sales - 1
    return {"consensus_sales": est, "guidance_sales": guidance_sales,
            "gap": gap, "stale": abs(gap) > 0.10}


def judge_multiples(peers, target_growth):
    """배수 적합성을 데이터로 판정한다. 손으로 고르지 않는다."""
    out = {}
    for key, gk in [("es27", "rev_g"), ("ee27", "eps_g"), ("per27", "eps_g")]:
        pts = [(x[gk], x[key]) for x in peers.values()
               if x.get(key) and x.get(gk) and x[key] > 0]
        if len(pts) < 5:
            continue
        xs, ys = zip(*pts)
        fit = linfit(xs, ys)
        fit["extrapolates"] = not (fit["xmin"] <= target_growth <= fit["xmax"])
        out[key] = fit
    return out


def relative_value(peers, target_ticker, base_sales, base_ebitda, market):
    """동종군 사분위로 범위를 낸다. 회귀 외삽은 하지 않는다."""
    others = {t: x for t, x in peers.items() if t != target_ticker}
    rows = []
    for key, label, base in [("ee27", "EV/EBITDA", base_ebitda),
                             ("es27", "EV/Sales", base_sales)]:
        vals = sorted(x[key] for x in others.values() if x.get(key) and x[key] > 0)
        if len(vals) < 4 or not base:
            continue
        q = {"동종 1사분위": vals[len(vals) // 4], "동종 중앙값": st.median(vals),
             "동종 3사분위": vals[3 * len(vals) // 4]}
        for name, mult in q.items():
            p = per_share(mult * base, market["shares"], market["net_debt"])
            rows.append({"multiple": label, "basis": name, "mult": mult,
                         "price": p, "upside": p / market["price"] - 1})
    return rows, st.median([r["price"] for r in rows])


# ────────────────────────── 텐베거 판정 ──────────────────────────

MCAP_IMPOSSIBLE = 200_000   # 백만 달러. 10배면 2조 달러로 세계 최상위 소수만 닿는다


def tenbagger(cfg, years=2, first_year=2027):
    """보유 기간 끝 시점의 주당가치를 시나리오별로 직접 구하고 확률가중한다.

    `매출배수 × 마진배수` 로만 보면 배수가 내내 그대로라고 가정하게 된다.
    그 축소를 빼면 텐베거 판정이 목표주가와 정반대로 나온다 (실측).

    2년에 10배는 연복리 216% 다. 매출과 배수가 함께 폭증해야 나오므로
    결과가 크게 갈리는 기업에서만 가능하다. 그 산포를 `spread` 로 낸다.
    """
    m, f = cfg["market"], cfg["fundamentals"]
    P, SH, ND = m["price"], m["shares"], m["net_debt"]
    mcap = P * SH
    ev_now = mcap + ND
    sales_now = f.get("guidance_sales_f1") or f["last_actual_revenue"]
    final_year = first_year + years - 1

    rows, weighted = {}, 0.0
    for name, s in cfg["scenarios"].items():
        rev = project_revenue(s["revenue"], s["tail_growth"])
        n = len(rev)
        opm = s["opm"] + [s["opm"][-1]] * (n - len(s["opm"]))
        sbc = s["sbc_pct"] if isinstance(s["sbc_pct"], list) else [s["sbc_pct"]] * n
        sbc = sbc + [sbc[-1]] * (n - len(sbc))
        r = dcf(rev, opm, sbc, s["tax"], s["nwc_pct"], s["wacc"], s["g"],
                f["last_actual_revenue"])
        fcfs = [x["fcf"] for x in r["rows"]]

        # 보유 기간 끝 시점의 기업가치. 그때 남은 현금흐름과 잔존가치를 그 시점으로 할인한다
        tv = fcfs[-1] * (1 + s["g"]) / (s["wacc"] - s["g"])
        rest = fcfs[years:]
        ev_end = sum(x / (1 + s["wacc"]) ** (i + 1) for i, x in enumerate(rest))
        ev_end += tv / (1 + s["wacc"]) ** len(rest)
        cum_fcf = sum(fcfs[:years])   # 보유 기간에 쌓인 현금. 배당과 자사주는 없다고 본다
        ps_end = (ev_end + cum_fcf - ND) / SH
        mult = ps_end / P
        weighted += s["probability"] * mult
        rows[name] = {
            "p": s["probability"], "revenue_end": rev[years - 1],
            "opm_end": opm[years - 1], "fcf_end": fcfs[years - 1],
            "ev_end": ev_end, "cum_fcf": cum_fcf, "ps_end": ps_end,
            "multiple": mult, "cagr": mult ** (1 / years) - 1,
            "ev_sales_end": ev_end / rev[years - 1],
        }

    base = cfg["scenarios"]["기본"]
    rev_base = project_revenue(base["revenue"], base["tail_growth"])
    opm_base = base["opm"] + [base["opm"][-1]] * (len(rev_base) - len(base["opm"]))
    ev_sales_now = ev_now / sales_now
    ev_sales_end = rows["기본"]["ev_sales_end"]

    tam, tam_year = f.get("tam"), f.get("tam_year")
    if tam and tam_year != final_year:
        tam = None

    mults = [r["multiple"] for r in rows.values()]
    best = max(rows, key=lambda k: rows[k]["multiple"])
    return {
        "years": years, "final_year": final_year,
        "spread": max(mults) / min(mults) if min(mults) > 0 else float("inf"),
        "best_multiple": max(mults), "best_scenario": best,
        "best_probability": rows[best]["p"],
        "current_mcap": mcap, "target_mcap": mcap * 10,
        "required_cagr": 10 ** (1 / years) - 1,
        "scenarios": rows, "weighted_multiple": weighted,
        "weighted_cagr": weighted ** (1 / years) - 1,
        # 분해는 설명용이다. 판정은 위의 직접 계산이 한다
        "revenue_multiple": rev_base[years - 1] / f["last_actual_revenue"],
        "margin_multiple": (opm_base[years - 1] / f["current_opm"]
                            if f.get("current_opm") else 1.0),
        "ev_sales_now": ev_sales_now, "ev_sales_end": ev_sales_end,
        "rerating": ev_sales_end / ev_sales_now,
        "terminal_revenue": rev_base[years - 1],
        "tam": tam, "tam_year": tam_year,
        "tam_share_needed": rev_base[years - 1] / tam if tam else None,
        "verdict": _tenbagger_verdict(mcap, weighted, max(mults)),
    }


def _tenbagger_verdict(mcap, weighted, best):
    """2년에 10배는 연복리 216% 다. 확률가중으로는 거의 나오지 않으므로
    최선 시나리오가 닿는지를 함께 본다."""
    if mcap > MCAP_IMPOSSIBLE:
        return ("불가", f"시가총액이 {mcap/100:,.0f}억 달러다. "
                f"10배면 {mcap*10/1_000_000:,.1f}조 달러로 세계 최상위 소수만 닿는 규모다")
    if weighted >= 10:
        return ("가능", f"확률가중 {weighted:.1f}배로 10배에 닿는다")
    if best >= 10:
        return ("최선 시나리오만", f"최선 시나리오가 {best:.1f}배지만 확률가중은 {weighted:.1f}배다")
    if best >= 4:
        return ("미달", f"최선 시나리오도 {best:.1f}배다. 매출과 배수가 함께 폭증하는 경로가 없다")
    return ("미달", f"최선 시나리오 {best:.1f}배, 확률가중 {weighted:.1f}배다")


# ────────────────────────────── 판정 ──────────────────────────────
#
# 절대가치와 상대가치를 가중평균하지 않는다.
# 둘은 다른 질문에 답하므로 평균은 어느 질문에도 답하지 못한다.
#   절대가치 — 이 사업이 벌어들일 현금의 오늘 값은 얼마인가
#   상대가치 — 시장이 같은 부류에 매기는 값은 얼마인가
# 두 답이 갈리면 그 차이 자체가 결론이다.


def judge_absolute(scen, weighted, price):
    """DCF 시나리오 안에서 상방과 하방을 잡는다."""
    ps = {k: v["ps"] for k, v in scen.items()}
    up, down = max(ps.values()), min(ps.values())
    up_r, down_r = up / price - 1, down / price - 1
    ratio = abs(up_r) / abs(down_r) if down_r < 0 else float("inf")
    return {"fair": weighted, "upside": weighted / price - 1,
            "high": up, "low": down, "up": up_r, "down": down_r,
            "risk_reward": ratio, "call": _call(weighted / price - 1, ratio),
            "entry": entry_prices(down, up, price)}


def judge_relative(rows, price):
    """동종 사분위 범위로 본다. 중앙값을 정답으로 두지 않는다."""
    if not rows:
        return None
    ps = sorted(r["price"] for r in rows)
    lo, mid, hi = ps[0], ps[len(ps) // 2], ps[-1]
    up_r, down_r = hi / price - 1, lo / price - 1
    ratio = abs(up_r) / abs(down_r) if down_r < 0 else float("inf")
    return {"fair": mid, "upside": mid / price - 1,
            "high": hi, "low": lo, "up": up_r, "down": down_r,
            "risk_reward": ratio, "call": _call(mid / price - 1, ratio),
            "entry": entry_prices(lo, hi, price)}


def _call(upside, ratio):
    if upside > 0.30 and ratio >= 2:
        return "매수"
    if upside > 0.10 and ratio >= 1:
        return "비중 확대"
    if upside < -0.20:
        return "비중 축소"
    return "보유"


def entry_prices(low, high, price):
    """상방과 하방 사이에서 원하는 손익비가 나오는 가격을 역산한다.

    (상방 − P) ÷ (P − 하방) = k  →  P = (상방 + k×하방) ÷ (1 + k)
    """
    return {f"{k:.0f}:1": (high + k * low) / (1 + k) for k in (1.0, 2.0, 3.0)}


def disagreement(absolute, relative):
    """두 방법이 얼마나, 왜 갈리는지 낸다. 합치지 않는다."""
    if not relative:
        return None
    gap = relative["fair"] / absolute["fair"] - 1
    if abs(gap) < 0.20:
        note = "두 방법이 같은 답을 낸다. 시장이 이 사업의 현금흐름을 그대로 값에 담고 있다"
    elif gap > 0:
        note = ("상대가치가 절대가치보다 높다. 시장이 같은 부류에 매기는 값 자체가 "
                "현금흐름으로 정당화되는 수준을 넘는다. 섹터가 재평가되면 함께 내려온다")
    else:
        note = ("절대가치가 상대가치보다 높다. 이 기업의 현금흐름이 같은 부류의 평균보다 "
                "낫다는 뜻이다. 시장이 아직 그것을 반영하지 않았다")
    return {"gap": gap, "note": note}


# ────────────────────────────── 실행 ──────────────────────────────

def load(ticker):
    p = INPUTS / f"{ticker}.json"
    if not p.exists():
        raise SystemExit(f"가정 파일이 없다: {p}")
    return json.loads(p.read_text())

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ticker = sys.argv[1].upper()
    as_json = "--json" in sys.argv
    cfg = load(ticker)
    m, f = cfg["market"], cfg["fundamentals"]
    P = m["price"]

    scen, weighted = run_scenarios(cfg)
    rev = reverse_dcf(cfg)
    peers = prep_peers({x["t"]: x for x in cfg["peers"]})
    tgt = peers[ticker]
    chk = consensus_check(tgt, f["guidance_sales_f2"])
    base_sales = f["guidance_sales_f2"] if chk["stale"] else tgt["sales_f2"]
    base_ebitda = base_sales * f["ebitda_margin_f2"]
    growth = base_sales / f["guidance_sales_f1"] - 1
    fits = judge_multiples({t: x for t, x in peers.items() if t != ticker}, growth)
    rel_rows, rel_ps = relative_value(peers, ticker, base_sales, base_ebitda, m)

    absolute = judge_absolute(scen, weighted, P)
    relative = judge_relative(rel_rows, P)
    gapinfo = disagreement(absolute, relative)
    ten = tenbagger(cfg, years=cfg.get("horizon_years", 2))

    result = {"ticker": ticker, "name": cfg["name"], "asof": cfg["asof"],
              "market": m, "fundamentals": f,
              "assumptions": {k: {"wacc": x["wacc"], "g": x["g"], "tax": x["tax"],
                                  "probability": x["probability"],
                                  "rationale": x.get("rationale", ""),
                                  "revenue_source": x.get("revenue_source", [])}
                              for k, x in cfg["scenarios"].items()},
              "probability_basis": cfg.get("probability_basis", ""),
              "scenarios": scen, "dcf_weighted": weighted, "reverse": rev,
              "consensus_check": chk, "multiple_fits": fits,
              "relative_rows": rel_rows, "relative_ps": rel_ps,
              "absolute": absolute, "relative": relative, "disagreement": gapinfo,
              "tenbagger": ten, "peers": peers, "base_sales": base_sales,
              "base_ebitda": base_ebitda, "target_growth": growth}

    if as_json:
        print(json.dumps(result, ensure_ascii=False, default=float))
        return

    print(f'{cfg["name"]} ({ticker})  기준일 {cfg["asof"]}  현재가 ${P}  '
          f'시가총액 {P*m["shares"]/100:,.0f}억 달러\n')

    n_years = len(scen["기본"]["rows"])
    print(f"── 절대가치: DCF ({n_years}년 명시 예측 + 잔존가치) ──")
    for name, r in scen.items():
        s = cfg["scenarios"][name]
        print(f'  {name:4} 확률 {r["p"]:4.0%}  주당 ${r["ps"]:8.2f} ({r["upside"]:+6.1%})  '
              f'g {s["g"]:.1%}  WACC {s["wacc"]:.1%}  잔존가치 {r["tv_share"]:.0%}')
    a = absolute
    print(f'  확률가중 ${a["fair"]:.2f} ({a["upside"]:+.1%})   '
          f'상방 ${a["high"]:.2f} ({a["up"]:+.0%})  하방 ${a["low"]:.2f} ({a["down"]:+.0%})')
    print(f'  손익비 {a["risk_reward"]:.2f}:1 → {a["call"]}')
    print('  진입가  ' + "  ".join(f'{k} ${v:,.2f} ({v/P-1:+.0%})'
                                  for k, v in a["entry"].items()) + "\n")

    print("── 역DCF: 현재 주가가 전제하는 것 ──")
    print(f'  할인율 {rev["implied_wacc"]:.2%}  또는 {rev["years"]}년 매출 CAGR '
          f'{rev["implied_cagr"]:.1%}  또는 영구성장률 {rev["implied_g"]:.2%}  '
          f'또는 영업이익률 {rev["implied_opm"]:.1%}\n')

    print("── 컨센서스 검증 ──")
    print(f'  제공자 추정 {chk["consensus_sales"]:,.0f}  가이던스 {chk["guidance_sales"]:,.0f}  '
          f'괴리 {chk["gap"]:+.1%}  '
          f'{"갱신 안 됨 → 가이던스로 교체" if chk["stale"] else "정합"}\n')

    print("── 상대가치 ──")
    for k, fit in fits.items():
        print(f'  {k:8} R²={fit["r2"]:.2f}  적합 구간 {fit["xmin"]*100:5.1f}~{fit["xmax"]*100:5.1f}%'
              f'  대상 {growth*100:.0f}% → {"외삽" if fit["extrapolates"] else "사용 가능"}')
    for r in rel_rows:
        print(f'  {r["multiple"]:10} {r["basis"]:12} {r["mult"]:6.1f}배 → '
              f'${r["price"]:8.2f} ({r["upside"]:+6.1%})')
    rl = relative
    print(f'  중앙 ${rl["fair"]:.2f} ({rl["upside"]:+.1%})   '
          f'상방 ${rl["high"]:.2f} ({rl["up"]:+.0%})  하방 ${rl["low"]:.2f} ({rl["down"]:+.0%})')
    print(f'  손익비 {rl["risk_reward"]:.2f}:1 → {rl["call"]}\n')

    print("── 두 방법의 차이 ──")
    print(f'  상대가치가 절대가치보다 {gapinfo["gap"]:+.1%}')
    print(f'  {gapinfo["note"]}\n')

    t = ten
    print(f'── 텐베거 판정 ({t["years"]}년, {t["final_year"]}년 기준) ──')
    print(f'  10배에 필요한 연복리 {t["required_cagr"]:.0%}  '
          f'시총 {t["current_mcap"]/100:,.0f}억 → {t["target_mcap"]/100:,.0f}억 달러\n')
    print(f'  {"시나리오":<6}{"확률":>6}{"기말매출":>10}{"그때 EV/S":>11}'
          f'{"기말 주당":>12}{"배수":>7}{"연복리":>9}')
    for name, r in t["scenarios"].items():
        print(f'  {name:<6}{r["p"]*100:>5.0f}%{r["revenue_end"]:>10,.0f}'
              f'{r["ev_sales_end"]:>10.1f}배${r["ps_end"]:>10,.2f}'
              f'{r["multiple"]:>6.1f}배{r["cagr"]*100:>+8.1f}%')
    print(f'\n  확률가중 {t["weighted_multiple"]:.1f}배 (연복리 {t["weighted_cagr"]:+.1%})  '
          f'최선 {t["best_scenario"]} {t["best_multiple"]:.1f}배 (확률 {t["best_probability"]:.0%})')
    print(f'  진폭 {t["spread"]:.1f}배 — 최선과 최악의 비율. 클수록 단기 텐베거 여지가 있다')
    print(f'  분해: 매출 {t["revenue_multiple"]:.1f}배 × 마진 {t["margin_multiple"]:.2f}배 '
          f'× 배수 {t["rerating"]:.2f}배 (EV/Sales {t["ev_sales_now"]:.1f} → {t["ev_sales_end"]:.1f})')
    print(f'  판정: {t["verdict"][0]} — {t["verdict"][1]}')


if __name__ == "__main__":
    main()
