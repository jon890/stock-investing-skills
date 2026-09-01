"""검증된 병목 그룹에서 종목 후보를 고르고 가치평가를 연결한다.

사용법:
    python3 tenbagger_pick.py reports/universe-USA-20260828.json --group 5710 --basis basis.json --json
    python3 tenbagger_pick.py reports/universe-USA-20260828.json --ticker CRDO --basis basis.json --json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bottleneck
import valuation


def score_universe(universe_path):
    path = Path(universe_path)
    data = json.loads(path.read_text())
    stocks, _ = bottleneck.validate_universe(data)
    groups, _ = bottleneck.aggregate(stocks)
    groups = bottleneck.score(groups)
    ranked = sorted(groups.values(), key=lambda value: -value["score"])
    rank_by_group = {value["group"]: index + 1 for index, value in enumerate(ranked)}
    return path, groups, rank_by_group


def load_group_context(universe_path, group_code, basis=None, include_candidates=False):
    path, groups, rank_by_group = score_universe(universe_path)
    if group_code not in groups:
        available = ", ".join(
            code for code, _ in sorted(rank_by_group.items(), key=lambda item: item[1])[:8]
        )
        raise SystemExit(f"{group_code} 그룹을 찾지 못했습니다. 상위 그룹 예시는 {available} 입니다.")
    group = groups[group_code]
    return bottleneck.serialize_group(
        group,
        rank_by_group[group_code],
        universe_path=path,
        basis=basis,
        include_candidates=include_candidates,
    )


def load_ticker_context(universe_path, ticker, basis=None):
    path, groups, rank_by_group = score_universe(universe_path)
    group, member = bottleneck.find_ticker(groups, ticker)
    if not group:
        raise SystemExit(f"{ticker.upper()} 티커를 유니버스에서 찾지 못했습니다.")
    context = bottleneck.serialize_group(
        group,
        rank_by_group[group["group"]],
        universe_path=path,
        basis=basis,
        include_candidates=False,
    )
    context["ticker"] = {
        "ticker": member["t"],
        "name": member["name"],
        "mcap": member["val"].get("mcap"),
        "rev_g": member["d"]["rev_g"],
        "margin_delta": member["d"]["margin_delta"],
        "screen": bottleneck.candidate_screen(member),
    }
    return context


def context_reasons(context):
    reasons = []
    if not context["is_bottleneck_group"]:
        reasons.append("산업 그룹이 병목 상위권을 통과하지 못했다.")
    if not context["bottleneck_basis"]["verified"]:
        missing = ", ".join(context["bottleneck_basis"]["missing"]) or "검증 근거"
        reasons.append(f"병목 실체 확인이 부족하다: {missing}.")
    return reasons


def analyze_group(group_code, universe_path, basis=None):
    context = load_group_context(
        universe_path, group_code, basis=basis, include_candidates=True
    )
    candidates = context.pop("candidates")
    reasons = context_reasons(context)
    status = "screenable" if not reasons else "reference_only"
    for candidate in candidates:
        candidate["candidate_status"] = status
    return {
        "group_code": group_code,
        "candidate_pool_status": status,
        "candidate_pool_reasons": reasons,
        "bottleneck_context": context,
        "candidates": candidates,
    }


def candidate_status(context, valuation_result):
    reasons = context_reasons(context)
    screen = context["ticker"]["screen"]
    if not screen["passed"]:
        reasons.extend(screen["reasons"])
    if not valuation_result["candidate"]["eligible"]:
        reasons.extend(valuation_result["candidate"]["reasons"])
    if reasons:
        return {"status": "reference_only", "reasons": reasons}
    return {"status": "candidate", "reasons": []}


def analyze_ticker(ticker, universe_path, basis=None):
    ticker = ticker.upper()
    context = load_ticker_context(universe_path, ticker, basis=basis)
    valuation_result = valuation.analyze(ticker)
    status = candidate_status(context, valuation_result)
    return {
        "ticker": ticker,
        "candidate_status": status["status"],
        "candidate_status_reasons": status["reasons"],
        "bottleneck_context": context,
        "valuation": valuation_result,
    }


def analyze(ticker, universe_path, basis=None):
    """기존 Python 호출자를 위한 티커 분석 호환 함수다."""
    return analyze_ticker(ticker, universe_path, basis=basis)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("universe", help="시장 유니버스 JSON 경로")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--group", help="후보를 찾을 TRBC 산업 그룹")
    target.add_argument("--ticker", help="역방향으로 병목 여부를 확인할 티커")
    parser.add_argument("--basis", help="병목 실체와 출처를 담은 JSON 경로")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력한다")
    return parser.parse_args()


def main():
    args = parse_args()
    basis = bottleneck.load_basis(args.basis)
    if args.group:
        result = analyze_group(args.group, args.universe, basis=basis)
        label = f'{args.group} 후보 풀 상태: {result["candidate_pool_status"]}'
        reasons = result["candidate_pool_reasons"]
    else:
        result = analyze_ticker(args.ticker, args.universe, basis=basis)
        label = f'{result["ticker"]} 후보 상태: {result["candidate_status"]}'
        reasons = result["candidate_status_reasons"]
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=float))
        return
    print(label)
    for reason in reasons:
        print(f"  - {reason}")
    if args.group:
        for candidate in result["candidates"]:
            print(f'  {candidate["ticker"]:6} {candidate["name"]}')


if __name__ == "__main__":
    main()
