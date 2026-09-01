"""섹터 병목 점수. 어느 산업 그룹이 가치사슬의 처리량을 제한하고 있는지 정량 판정한다.

병목이란 수요가 공급을 초과해 그 구간이 전체 처리량을 제한하는 상태다.
병목 구간은 가격결정력을 쥐고 초과이윤을 가져간다. 텐베거는 여기서 나온다.

사용법:
    python3 bottleneck.py reports/universe-USA-20260828.json
    python3 bottleneck.py reports/universe-USA-20260828.json --json
    python3 bottleneck.py reports/universe-USA-20260828.json --json --output reports/bottleneck-USA-20260828.json
    python3 bottleneck.py reports/universe-USA-20260828.json --group 5710
    python3 bottleneck.py reports/universe-USA-20260828.json --ticker CRDO --json
"""
from __future__ import annotations
import json, sys, statistics as st
from datetime import date
from pathlib import Path

# ────────────── 병목의 다섯 가지 증거와 가중치 ──────────────
# 가중치는 3년 안에 10배라는 목표에서 역산한다. 연복리로 115% 다.
# 시가총액 = 매출 × 이익률 × 배수 이므로 세 항이 함께 커져야 10배가 된다.
# 3년이면 매출 3배, 마진 1.6배, 배수 2배 정도의 조합이다.
#   매출 항  → 수요 수준 28%
#   이익률 항 → 가격결정력 22%
#   배수 항  → 미반영 여지 30% + 기대 분산 12% = 42%
#   확인 신호 → 자금 집중 8%
# 10년 목표였을 때와 견주면 미반영 여지가 10% 에서 30% 로 올랐고 기대 분산이 새로 들어왔다.
# 3년 안에 10배는 배수 확대 없이 나오지 않으므로 배수 항이 목표의 가장 큰 몫을 갖는다.
# 반대로 자금 집중은 20% 에서 8% 로 내렸다. 이미 오른 곳에 점수를 주는 축이기 때문이다.
# 지속성(초과수익의 기간 일관성)은 뺐다. 10년 목표에서 테마와 구조를 가르던 축인데
# 3년 구간에서는 병목 실체 확인이 같은 일을 더 직접 한다.
#
# 수요 가속을 넣으려 했으나 데이터가 없어 뺐다. 실측 근거는 CLAUDE.md 에 있다.
# LTM 배수로 직전 구간 성장률을 역산하면 391개 중 362개가 상한에 붙는다.
# valley 의 LTM 은 한 회계연도 이상 낡아 있다. 감속 여부는 사람이 병목 실체 확인에서 본다.
FACTORS = {
    "demand":     ("수요 수준",   0.28, "매출 성장률. 3년 복리로 매출 3배를 만드는 축이다"),
    "pricing":    ("가격결정력", 0.22, "이익률 확대. 병목과 단순 성장을 가른다"),
    "headroom":   ("미반영 여지", 0.30, "성장 대비 배수가 낮은 정도. 배수 2배 확대 여지다"),
    "dispersion": ("기대 분산",   0.12, "목표주가가 갈리는 폭. 결과가 갈리는 곳에서만 10배가 나온다"),
    "capital":    ("자금 집중",   0.08, "시장 대비 초과수익. 이것을 빼면 침체 산업이 여지 하나로 1위가 된다"),
}
# 초과수익을 볼 기간과 가중치. 3년 목표이므로 한 달 반등보다 분기 흐름을 무겁게 둔다.
RETURN_WINDOWS = {"1m": 0.25, "3m": 0.30, "6m": 0.25, "ytd": 0.10, "1y": 0.10}
MIN_MEMBERS = 3          # 종목이 이보다 적은 그룹은 통계가 성립하지 않는다
MIN_RETURN_COVERAGE = 0.98  # 기간 수익률이 이보다 적으면 병목 점수를 믿지 않는다
WINSOR = 0.02            # 이상치가 z 점수를 무너뜨리므로 양끝을 절단한다
Z_CAP = 2.5              # 절단 뒤에도 남는 이상치의 표준점수 상한
CAPITAL_EXIT = -1.0      # 자금 집중이 이보다 낮으면 이탈 중으로 본다
BOTTLENECK_GROUP_LIMIT = 3

SECTOR_NAME = {"50": "에너지", "51": "소재", "52": "산업재", "53": "경기소비재",
               "54": "필수소비재", "55": "금융", "56": "헬스케어", "57": "기술",
               "58": "통신", "59": "유틸리티", "60": "리츠"}


# ────────────── 종목 단위 파생 지표 ──────────────

def derive(x):
    """배수에서 성장률과 마진을 역산한다. 추정이 없으면 None 을 남긴다."""
    v = x["val"]
    d = {}
    esL, es26, es27 = v.get("esL"), v.get("es26"), v.get("es27")
    ee26, ee27 = v.get("ee26"), v.get("ee27")
    # 매출 성장률: EV 가 같으므로 EV/Sales 배수의 비율이 매출 비율의 역수가 된다
    d["rev_g"] = es26 / es27 - 1 if es26 and es27 and es27 > 0 else None
    # LTM 역산 매출. 배수 신선도 점검에만 쓴다. 성장률 계산에는 쓰지 않는다.
    # valley 의 LTM 은 한 회계연도 이상 낡아 있어 이것으로 직전 구간 성장률을
    # 역산하면 유니버스의 92% 가 비현실적인 감속으로 잡힌다 (실측).
    ev = v.get("ev")
    d["ltm_sales"] = ev / esL if ev and esL and esL > 0 else None
    # EBITDA 마진 = (EV/Sales) ÷ (EV/EBITDA)
    m26 = es26 / ee26 if es26 and ee26 and ee26 > 0 else None
    m27 = es27 / ee27 if es27 and ee27 and ee27 > 0 else None
    d["margin26"], d["margin27"] = m26, m27
    d["margin_delta"] = m27 - m26 if m26 is not None and m27 is not None else None
    d["es27"] = es27
    # 성장 대비 배수. 낮을수록 성장이 아직 값에 안 들어갔다
    d["price_of_growth"] = (es27 / (d["rev_g"] * 100)
                            if es27 and d["rev_g"] and d["rev_g"] > 0.02 else None)
    # 기대 분산. 목표주가의 최고와 최저가 벌어진 폭을 평균으로 나눈다.
    # 추정 기관이 셋 미만이면 폭이 기관 수의 우연이므로 버린다.
    tgt, tlo, thi = v.get("tgt"), v.get("tlo"), v.get("thi")
    nest = v.get("nest") or 0
    d["dispersion"] = ((thi - tlo) / tgt
                       if tgt and tlo and thi and tgt > 0 and nest >= 3 else None)
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
    """양 끝을 절단한다. 표본이 작으면 비율이 0개가 되므로 최소 한 개는 자른다."""
    s = sorted(xs)
    if len(s) < 5:
        return list(xs)
    k = max(1, int(len(s) * p))
    lo, hi = s[k], s[-1 - k]
    return [min(max(x, lo), hi) for x in xs]


def zscores(d):
    """{키: 값} 을 z 점수로. 값이 None 인 키는 0 으로 둔다(중립)."""
    keys = [k for k, v in d.items() if v is not None]
    if len(keys) < 2:
        return {k: 0.0 for k in d}
    vals = winsorize([d[k] for k in keys])
    mu = st.fmean(vals)
    sd = st.pstdev(vals) or 1.0
    # 절단 뒤에도 남는 이상치가 한 팩터로 순위를 뒤집지 않게 z 를 제한한다
    z = {k: max(-Z_CAP, min(Z_CAP, (v - mu) / sd)) for k, v in zip(keys, vals)}
    return {k: z.get(k, 0.0) for k in d}


def return_quality(stocks):
    """기간별 수익률 결측을 세어 입력 데이터의 신뢰도를 판정한다."""
    total = len(stocks)
    missing = {
        p: sum(1 for x in stocks if x.get("ret", {}).get(p) is None)
        for p in RETURN_WINDOWS
    }
    coverage = {
        p: ((total - n) / total if total else 0.0)
        for p, n in missing.items()
    }
    return {
        "missing_return_by_period": missing,
        "return_coverage": coverage,
        "min_return_coverage": min(coverage.values()) if coverage else 0.0,
        "threshold": MIN_RETURN_COVERAGE,
    }


def validate_universe(data):
    stocks = data.get("stocks") or []
    if not stocks:
        raise SystemExit("입력 JSON에 stocks가 없습니다.")
    q = return_quality(stocks)
    bad = [p for p, c in q["return_coverage"].items() if c < MIN_RETURN_COVERAGE]
    if bad:
        detail = ", ".join(
            f"{p} {q['return_coverage'][p]*100:.1f}%"
            f"({q['missing_return_by_period'][p]}개 결측)"
            for p in bad
        )
        raise SystemExit(
            f"기간 수익률 커버리지가 낮아 병목 점수를 중단합니다: {detail}. "
            f"최소 {MIN_RETURN_COVERAGE*100:.0f}%가 필요합니다."
        )
    return stocks, q


def factor_gap_text(group):
    gaps = "  ".join(
        f'{FACTORS[f][0]} {(1-c)*100:.0f}%'
        for f, c in group["coverage"].items()
        if c < 1.0
    )
    return gaps or "없음"


def opt_value(flag):
    if flag not in sys.argv:
        return None
    try:
        return sys.argv[sys.argv.index(flag) + 1]
    except IndexError:
        raise SystemExit(f"{flag} 뒤에 값이 필요합니다.")


def emit_json(payload, output_path=None):
    body = json.dumps(payload, ensure_ascii=False, default=float)
    if output_path:
        Path(output_path).write_text(body + "\n")
        print(f"작성: {output_path}")
    else:
        print(body)


def sector_label(group_code):
    return SECTOR_NAME.get(group_code[:2], "")


# ────────────── 그룹 집계 ──────────────

def aggregate(stocks):
    """산업 그룹 단위로 묶고 팩터 원값을 만든다."""
    groups = {}
    for x in stocks:
        x["d"] = derive(x)
        groups.setdefault(x["g"], []).append(x)

    market_cap = sum(x["cap"] for x in stocks)
    market_ret = {}
    for p in RETURN_WINDOWS:
        r = wmean([(x["ret"].get(p), x["cap"]) for x in stocks])
        if r is None:
            raise SystemExit(f"{p} 시장 수익률을 계산할 수 없습니다. 기간 수익률이 모두 결측입니다.")
        market_ret[p] = r

    out = {}
    for g, members in groups.items():
        if len(members) < MIN_MEMBERS:
            continue
        cap = sum(m["cap"] for m in members)
        w = lambda f: wmean([(f(m), m["cap"]) for m in members])

        group_ret = {
            p: wmean([(m["ret"].get(p), m["cap"]) for m in members])
            for p in RETURN_WINDOWS
        }
        excess = {p: (None if group_ret[p] is None else group_ret[p] - market_ret[p])
                  for p in RETURN_WINDOWS}
        capital = wmean([(excess[p], wt) for p, wt in RETURN_WINDOWS.items()])
        # 초과수익이 양수인 기간의 비율. 점수에는 안 쓰고 테마 여부 확인용으로만 남긴다.
        visible_excess = [v for v in excess.values() if v is not None]
        persistence = (2 * sum(1 for v in visible_excess if v > 0) / len(visible_excess) - 1
                       if visible_excess else None)

        pg = w(lambda m: m["d"]["price_of_growth"])
        out[g] = {
            "group": g, "sector": g[:2], "n": len(members), "cap": cap,
            "cap_share": cap / market_cap,
            "raw": {
                "demand": w(lambda m: m["d"]["rev_g"]),
                "pricing": w(lambda m: m["d"]["margin_delta"]),
                # 성장 대비 배수는 낮을수록 좋으므로 부호를 뒤집는다
                "headroom": -pg if pg is not None else None,
                "dispersion": w(lambda m: m["d"]["dispersion"]),
                "capital": capital,
            },
            "persistence": persistence,
            "excess": excess,
            "return_coverage": {p: sum(1 for m in members if m["ret"].get(p) is not None) / len(members)
                                for p in RETURN_WINDOWS},
            "margin27": w(lambda m: m["d"]["margin27"]),
            "es27": w(lambda m: m["d"]["es27"]),
            "price_of_growth": pg,
            "coverage": {f: sum(1 for m in members if m["d"].get(k) is not None) / len(members)
                         for f, k in (("demand", "rev_g"),
                                      ("pricing", "margin_delta"),
                                      ("headroom", "price_of_growth"),
                                      ("dispersion", "dispersion"))},
            "top": sorted(members, key=lambda m: -m["cap"])[:5],
            "members": members,
        }
    return out, market_ret


def score(groups):
    """팩터별 z 점수를 내고 가중합한다.

    미반영 여지는 병목으로 판정된 그룹에서만 양수로 인정한다.
    수요와 가격결정력이 받쳐주지 않는 낮은 배수는 텐베거 여지가 아니라
    그냥 시장이 값을 낮게 매긴 상태다. 자금이 크게 이탈 중인 그룹도 마찬가지로,
    배수가 낮은 것이 아니라 값이 무너지는 중이다.
    이 조건이 없으면 침체 산업이 미반영 여지 하나로 1위가 된다
    (실측: 2026-08-29 자동차 그룹이 1년 초과수익 -45% 로 1위였다).
    """
    for f in FACTORS:
        z = zscores({g: v["raw"][f] for g, v in groups.items()})
        for g, v in groups.items():
            # 팩터 결측이 많으면 그만큼 중립으로 수축시킨다.
            # 결측을 그대로 두면 소수의 종목이 그룹 전체를 대표하게 된다.
            c = v["coverage"].get(f, 1.0)
            v.setdefault("z", {})[f] = z[g] * c
    for v in groups.values():
        z = v["z"]
        if z["headroom"] > 0:
            if not (z["demand"] > 0 and z["pricing"] > 0):
                v["headroom_voided"] = "수요나 가격결정력이 음수다"
            elif z["capital"] < CAPITAL_EXIT:
                v["headroom_voided"] = "자금이 이탈 중이다"
        if v.get("headroom_voided"):
            z["headroom"] = 0.0
        v["score"] = sum(z[f] * FACTORS[f][1] for f in FACTORS)
    return groups


# ────────────── 텐베거 후보 ──────────────

MCAP_CEILING = 50_000      # 백만 달러. 10배면 5,000억 달러다
MCAP_SWEET = 10_000        # 이 아래가 10배 여지가 가장 크다


def candidate_screen(member):
    """종목이 병목 수혜 후보의 최소 조건을 통과하는지 판정한다."""
    cap = member["val"].get("mcap")
    data = member["d"]
    reasons = []
    if not cap:
        reasons.append("시가총액이 없다.")
    elif cap > MCAP_CEILING:
        reasons.append("시가총액이 500억 달러를 넘는다.")
    if data["rev_g"] is None or data["rev_g"] < 0.10:
        reasons.append("매출 성장률이 10% 미만이다.")
    if data["margin_delta"] is None or data["margin_delta"] <= 0:
        reasons.append("마진이 확대되지 않는다.")
    return {"passed": not reasons, "reasons": reasons}


def tenbagger_candidates(group, limit=8):
    """병목 그룹 안에서 3년 10배 여지가 남은 종목을 고른다.

    대형주는 병목의 수혜를 이미 가격에 담았다. 여지는 시총이 작은 쪽에 있다.
    진폭이 작은 기업은 최선의 경우에도 두세 배에 그치므로 기대 분산을 함께 본다.
    """
    out = []
    for m in group["members"]:
        cap, d, v = m["val"].get("mcap"), m["d"], m["val"]
        if not candidate_screen(m)["passed"]:
            continue
        size = 1.0 if cap <= MCAP_SWEET else MCAP_SWEET / cap
        # 순위는 병목 점수와 같은 축으로 매긴다. 그룹에서 쓴 다섯 팩터 중
        # 종목 단위로 계산되는 넷을 같은 순서로 쓴다. 분산은 가정 없이
        # 5년 매출 추정의 진폭을 근사하는 유일한 관측값이다.
        rank = (d["rev_g"] * 2.8
                + (d["margin_delta"] or 0.0) * 6.0
                + (d["dispersion"] or 0.0) * 1.2
                + size)
        out.append({
            "ticker": m["t"], "name": m["name"], "mcap": cap,
            "rev_g": d["rev_g"], "margin_delta": d["margin_delta"],
            "margin27": d["margin27"], "es27": d["es27"],
            "dispersion": d["dispersion"],
            "ret_1y": m["ret"].get("1y"), "ret_1m": m["ret"].get("1m"),
            "nest": v.get("nest"), "tgt": v.get("tgt"),
            "tlo": v.get("tlo"), "thi": v.get("thi"),
            "rank": rank,
        })
    ranked = sorted(out, key=lambda x: -x["rank"])
    return ranked if limit is None else ranked[:limit]


# ────────────── handoff 계약 ──────────────

RESEARCH_FIELDS = (
    "group_code", "constraint", "duration", "controller",
)
PASS_VERDICTS = {"pass", "통과"}
MIN_FACTOR_COVERAGE = 0.70


def valid_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def bottleneck_basis(raw=None, expected_group=None):
    """정량 점수와 별도로 사람이 확인한 병목 실체를 검증한다."""
    basis = dict(raw or {})
    sources = basis.get("sources") or []
    missing = [k for k in RESEARCH_FIELDS if not basis.get(k)]
    if not sources:
        missing.append("sources")
    if not valid_date(basis.get("reviewed_at")):
        missing.append("reviewed_at")
    if expected_group and basis.get("group_code") and basis["group_code"] != expected_group:
        missing.append("group_code_mismatch")
    if not isinstance(basis.get("duration_years"), (int, float)) or basis.get("duration_years", 0) <= 3:
        missing.append("duration_years>3")
    verified_sources = [
        s for s in sources
        if isinstance(s, dict) and s.get("title") and (s.get("url") or s.get("source_locator"))
        and valid_date(s.get("observed_at") or s.get("source_observed_at"))
    ]
    if len(verified_sources) != len(sources):
        missing.append("verified_sources")
    verdict = basis.get("verdict") or "unverified"
    basis.update({
        "constraint": basis.get("constraint"),
        "duration": basis.get("duration"),
        "controller": basis.get("controller"),
        "sources": sources,
        "verdict": verdict,
        "missing": sorted(set(missing)),
        "verified": verdict in PASS_VERDICTS and not missing,
    })
    return basis


def is_bottleneck_group(group, rank):
    z = group["z"]
    coverage_ok = all(group["coverage"].get(k, 0.0) >= MIN_FACTOR_COVERAGE for k in group["coverage"])
    return (
        rank <= BOTTLENECK_GROUP_LIMIT
        and group["score"] > 0
        and z["demand"] > 0
        and z["pricing"] > 0
        and coverage_ok
    )


def serialize_group(group, rank, universe_path=None, basis=None, include_candidates=False):
    """다음 스킬로 넘기는 최소 계약을 만든다."""
    basis_checked = bottleneck_basis(basis, expected_group=group["group"])
    out = {
        "universe_path": str(universe_path) if universe_path else None,
        "group_code": group["group"],
        "group_name": sector_label(group["group"]),
        "rank": rank,
        "score": group["score"],
        "is_bottleneck_group": is_bottleneck_group(group, rank),
        "bottleneck_basis": basis_checked,
        "quality": {
            "coverage": group["coverage"],
            "return_coverage": group.get("return_coverage", {}),
            "factor_gap": factor_gap_text(group),
        },
        "signals": {
            "raw": group["raw"],
            "z": group["z"],
            "excess": group["excess"],
            "persistence": group.get("persistence"),
        },
        "top": [{"t": m["t"], "name": m["name"], "cap": m["cap"]} for m in group["top"]],
    }
    out["candidate_pool_passed"] = out["is_bottleneck_group"] and basis_checked["verified"]
    if include_candidates:
        status = "screenable" if out["candidate_pool_passed"] else "reference_only"
        out["candidates"] = [
            {**c, "candidate_status": status}
            for c in tenbagger_candidates(group)
        ]
    return out


def load_basis(path):
    if not path:
        return None
    return json.loads(Path(path).read_text())


def find_ticker(groups, ticker):
    wanted = ticker.upper()
    for group in groups.values():
        for member in group["members"]:
            if member["t"].upper() == wanted:
                return group, member
    return None, None


# ────────────── 출력 ──────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    universe_path = Path(args[0])
    data = json.loads(universe_path.read_text())
    stocks, quality = validate_universe(data)
    groups, market_ret = aggregate(stocks)
    groups = score(groups)
    ranked = sorted(groups.values(), key=lambda v: -v["score"])
    rank_by_group = {v["group"]: i + 1 for i, v in enumerate(ranked)}
    as_json = "--json" in sys.argv
    group_arg = opt_value("--group")
    ticker_arg = opt_value("--ticker")
    basis = load_basis(opt_value("--basis"))
    output_path = opt_value("--output")
    if output_path and not as_json:
        raise SystemExit("--output은 --json과 함께 사용합니다.")

    if ticker_arg:
        group, member = find_ticker(groups, ticker_arg)
        if not group:
            raise SystemExit(f"{ticker_arg.upper()} 티커를 유니버스에서 찾지 못했습니다.")
        context = serialize_group(group, rank_by_group[group["group"]],
                                  universe_path=universe_path, basis=basis,
                                  include_candidates=False)
        context["ticker"] = {
            "ticker": member["t"], "name": member["name"],
            "mcap": member["val"].get("mcap"),
            "rev_g": member["d"]["rev_g"],
            "margin_delta": member["d"]["margin_delta"],
        }
        if as_json:
            emit_json({"market": data["market"], "bottleneck_context": context}, output_path)
            return
        print(f'{member["t"]} {member["name"]} — {group["group"]} {sector_label(group["group"])}')
        print(f'  병목 순위 {context["rank"]}위, 점수 {context["score"]:+.2f}')
        print(f'  병목 그룹 통과: {"예" if context["is_bottleneck_group"] else "아니오"}')
        print(f'  근거 검증: {"통과" if context["bottleneck_basis"]["verified"] else "미검증"}')
        return

    if group_arg:
        g = group_arg
        if g not in groups:
            available = ", ".join(v["group"] for v in ranked[:8])
            raise SystemExit(f"{g} 그룹을 찾지 못했습니다. 상위 그룹 예시는 {available} 입니다.")
        context = serialize_group(groups[g], rank_by_group[g],
                                  universe_path=universe_path, basis=basis,
                                  include_candidates=False)
        if as_json:
            emit_json({"market": data["market"], "bottleneck_context": context}, output_path)
            return
        v = groups[g]
        print(f'{g} {sector_label(g)} — 병목 점수 {v["score"]:+.2f}')
        print(f'  병목 순위 {context["rank"]}위, 구성 {v["n"]}개, 시총 {v["cap"]/1000:,.0f}십억 달러')
        print(f'  병목 그룹 통과: {"예" if context["is_bottleneck_group"] else "아니오"}')
        print(f'  근거 검증: {"통과" if context["bottleneck_basis"]["verified"] else "미검증"}')
        print(f'  대표 종목 ' + ", ".join(m["t"] for m in v["top"]))
        print(f'  팩터 결측 ' + factor_gap_text(v))
        return

    if as_json:
        for v in ranked:
            v.pop("members"); v["top"] = [{"t": m["t"], "name": m["name"],
                                           "cap": m["cap"]} for m in v["top"]]
        emit_json({"market": data["market"], "market_ret": market_ret,
                   "quality": {
                       "missing_valuation": data.get("missing_valuation"),
                       **quality,
                   },
                   "factors": {k: {"label": v[0], "weight": v[1], "why": v[2]}
                               for k, v in FACTORS.items()},
                   "groups": ranked}, output_path)
        return

    print(f'{data["market"]} 시장 산업 그룹 병목 점수  (종목 {data["count"]}개, '
          f'그룹 {len(groups)}개)\n')
    print("팩터와 가중치")
    for k, (label, w, why) in FACTORS.items():
        print(f'  {label:8} {w:4.0%}  {why}')
    print()
    hdr = (f'{"그룹":<6}{"섹터":<8}{"점수":>7}{"수요":>7}{"가격":>7}'
           f'{"여지":>7}{"분산":>7}{"자금":>7}{"성장%":>8}{"마진Δ":>8}{"시총":>10}')
    print(hdr); print("─" * 90)
    for v in ranked[:15]:
        r = v["raw"]
        f = lambda x, s=100: f"{x*s:+.1f}" if x is not None else "   -"
        print(f'{v["group"]:<6}{SECTOR_NAME.get(v["sector"],"?"):<8}{v["score"]:>+7.2f}'
              f'{v["z"]["demand"]:>+7.1f}{v["z"]["pricing"]:>+7.1f}'
              f'{v["z"]["headroom"]:>+7.1f}{v["z"]["dispersion"]:>+7.1f}{v["z"]["capital"]:>+7.1f}'
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
    print('  팩터 결측 ' + factor_gap_text(best))
    miss = quality["missing_return_by_period"]
    missing_text = "  ".join(f"{p} {n}개" for p, n in miss.items() if n)
    print("  기간 수익률 결측 " + (missing_text or "없음"))
    print(f'  기간별 초과수익  ' + "  ".join(
        f'{p} {best["excess"][p]:+.1f}%' for p in RETURN_WINDOWS))
    print('\n  종목 선별은 tenbagger-pick 단계에서 별도로 실행한다')


if __name__ == "__main__":
    main()
