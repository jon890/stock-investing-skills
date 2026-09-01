"""병목 그룹 안에서 텐베거 후보와 가치평가를 연결한다.

사용법:
    python3 tenbagger_pick.py CRDO reports/universe-USA-20260828.json --json
    python3 tenbagger_pick.py CRDO reports/universe-USA-20260828.json --basis basis.json --json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import bottleneck
import valuation


def opt_value(flag):
    if flag not in sys.argv:
        return None
    try:
        return sys.argv[sys.argv.index(flag) + 1]
    except IndexError:
        raise SystemExit(f"{flag} 뒤에 값이 필요합니다.")


def load_context(universe_path, ticker, basis=None):
    path = Path(universe_path)
    data = json.loads(path.read_text())
    stocks, _ = bottleneck.validate_universe(data)
    groups, _ = bottleneck.aggregate(stocks)
    groups = bottleneck.score(groups)
    ranked = sorted(groups.values(), key=lambda v: -v["score"])
    rank_by_group = {v["group"]: i + 1 for i, v in enumerate(ranked)}
    group, member = bottleneck.find_ticker(groups, ticker)
    if not group:
        raise SystemExit(f"{ticker.upper()} 티커를 유니버스에서 찾지 못했습니다.")
    context = bottleneck.serialize_group(
        group,
        rank_by_group[group["group"]],
        universe_path=path,
        basis=basis,
        include_candidates=True,
    )
    context["ticker"] = {
        "ticker": member["t"],
        "name": member["name"],
        "mcap": member["val"].get("mcap"),
        "rev_g": member["d"]["rev_g"],
        "margin_delta": member["d"]["margin_delta"],
    }
    return context


def candidate_status(context, valuation_result):
    reasons = []
    if not context["is_bottleneck_group"]:
        reasons.append("산업 그룹이 병목 상위권을 통과하지 못했다.")
    if not context["bottleneck_basis"]["verified"]:
        missing = ", ".join(context["bottleneck_basis"]["missing"]) or "검증 근거"
        reasons.append(f"병목 실체 확인이 부족하다: {missing}.")
    if not valuation_result["candidate"]["eligible"]:
        reasons.extend(valuation_result["candidate"]["reasons"])
    if reasons:
        return {"status": "reference_only", "reasons": reasons}
    return {"status": "candidate", "reasons": []}


def analyze(ticker, universe_path, basis=None):
    ticker = ticker.upper()
    context = load_context(universe_path, ticker, basis=basis)
    valuation_result = valuation.analyze(ticker)
    gate = candidate_status(context, valuation_result)
    return {
        "ticker": ticker,
        "candidate_status": gate["status"],
        "candidate_status_reasons": gate["reasons"],
        "bottleneck_context": context,
        "valuation": valuation_result,
    }


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    ticker = sys.argv[1]
    universe_path = sys.argv[2]
    basis = bottleneck.load_basis(opt_value("--basis"))
    result = analyze(ticker, universe_path, basis=basis)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, default=float))
        return
    print(f'{result["ticker"]} 후보 상태: {result["candidate_status"]}')
    for reason in result["candidate_status_reasons"]:
        print(f"  - {reason}")


if __name__ == "__main__":
    main()
