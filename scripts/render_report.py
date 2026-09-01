"""병목 점수와 밸류에이션 JSON 을 로컬 HTML 리포트로 렌더링한다.

사용법:
    python3 render_report.py bottleneck reports/bottleneck-USA-<날짜>.json KOR-JSON --context CONTEXT-JSON -o <출력>
    python3 render_report.py company    reports/valuation-<티커>-<날짜>.json  -o <출력>
"""
from __future__ import annotations
import json, sys, html
from pathlib import Path

SECTOR = {"50": "에너지", "51": "소재", "52": "산업재", "53": "경기소비재",
          "54": "필수소비재", "55": "금융", "56": "헬스케어", "57": "기술",
          "58": "통신", "59": "유틸리티", "60": "리츠"}

CSS = """
:root{--bg:#fbfbf9;--fg:#1c1c1a;--mut:#6b6b64;--line:#e2e1db;--card:#fff;
--up:#0a7d4f;--dn:#c0392b;--acc:#2d4f8e;--warn:#8a6d1f;--warnbg:#fdf8e8}
@media(prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#e8e8e4;--mut:#9a9a92;
--line:#2e2e34;--card:#1e1e23;--up:#4ade80;--dn:#f87171;--acc:#7aa2e3;
--warn:#d4b45a;--warnbg:#2a2413}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.65 -apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.3px}
h2{font-size:19px;margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:26px 0 10px;color:var(--mut);font-weight:600}
.sub{color:var(--mut);font-size:13px;margin-bottom:28px}
.verdict{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:22px 24px;margin:22px 0 8px}
.vgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:20px}
.vk{font-size:12px;color:var(--mut);margin-bottom:4px}
.vv{font-size:23px;font-weight:650;letter-spacing:-.5px}
.vn{font-size:12px;color:var(--mut);margin-top:2px}
.scroll{overflow-x:auto;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;
font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line);
white-space:nowrap}
th{font-weight:600;color:var(--mut);font-size:12px;text-align:right;
border-bottom:1.5px solid var(--line)}
th:first-child,td:first-child,.l{text-align:left}
tbody tr:hover{background:color-mix(in srgb,var(--acc) 6%,transparent)}
tr.hi{background:color-mix(in srgb,var(--acc) 9%,transparent);font-weight:600}
.up{color:var(--up)}.dn{color:var(--dn)}.mut{color:var(--mut)}
.note{background:var(--warnbg);border-left:3px solid var(--warn);
padding:12px 16px;margin:16px 0;font-size:13.5px;border-radius:0 6px 6px 0}
.note b{color:var(--warn)}
p{margin:10px 0}
ul{margin:10px 0;padding-left:20px}li{margin:5px 0}
.bar{display:inline-block;height:9px;border-radius:2px;vertical-align:middle;
margin-right:6px;min-width:2px}
code{background:color-mix(in srgb,var(--fg) 7%,transparent);padding:1px 5px;
border-radius:4px;font-size:12.5px}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
color:var(--mut);font-size:12px}
"""


def esc(s): return html.escape(str(s))
def pct(v, d=1, sign=True):
    if v is None: return '<span class="mut">-</span>'
    c = "up" if v > 0 else ("dn" if v < 0 else "mut")
    return f'<span class="{c}">{v*100:+.{d}f}%</span>' if sign else f"{v*100:.{d}f}%"
def num(v, d=1):
    return f"{v:,.{d}f}" if v is not None else '<span class="mut">-</span>'
def signed(v, d=1):
    return f"{v:+.{d}f}" if v is not None else '<span class="mut">-</span>'
def page(title, body):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body>'
            f'<div class="wrap">{body}</div></body></html>')


# ────────────────────── 병목 리포트 ──────────────────────

def render_bottleneck(usa, kor, asof, context_payload=None):
    F = usa["factors"]
    g = usa["groups"]
    best = g[0]
    quality = usa.get("quality", {})
    missing = quality.get("missing_return_by_period", {})
    missing_text = " · ".join(f"{esc(k)} {v}개" for k, v in missing.items() if v)
    if not missing_text:
        missing_text = "없음"

    cards = "".join(
        f'<div><div class="vk">{esc(v["label"])}</div>'
        f'<div class="vv">{v["weight"]*100:.0f}%</div>'
        f'<div class="vn">{esc(v["why"])}</div></div>' for v in F.values())

    def grow(v, rank):
        z = v["z"]
        cls = ' class="hi"' if rank == 0 else ""
        w = max(2, abs(v["score"]) * 46)
        col = "var(--up)" if v["score"] > 0 else "var(--dn)"
        return (f'<tr{cls}><td class="l">{v["group"]}</td>'
                f'<td class="l">{esc(SECTOR.get(v["sector"],"?"))}</td>'
                f'<td><span class="bar" style="width:{w}px;background:{col}"></span>'
                f'{v["score"]:+.2f}</td>'
                + "".join(f'<td>{z[k]:+.1f}</td>' for k in F)
                + f'<td>{pct(v["raw"]["demand"])}</td>'
                  f'<td>{pct(v["raw"]["pricing"])}</td>'
                  f'<td>{pct(v["raw"].get("dispersion"), 0, sign=False)}</td>'
                  f'<td>{pct(v.get("persistence"), 0)}</td>'
                  f'<td>{num(v["cap"]/1000,0)}B</td>'
                  f'<td class="l mut">{esc(", ".join(t["t"] for t in v["top"][:3]))}</td></tr>')

    rows = "".join(grow(v, i) for i, v in enumerate(g[:15]))
    fh = "".join(f'<th>{esc(v["label"])}</th>' for v in F.values())

    ex = best["excess"]
    exr = "".join(f'<td>{pct(None if v is None else v/100)}</td>' for v in ex.values())
    exh = "".join(f'<th>{k}</th>' for k in ex)

    krows = "".join(
        f'<tr><td class="l">{v["group"]}</td>'
        f'<td class="l">{esc(SECTOR.get(v["sector"],"?"))}</td>'
        f'<td>{v["score"]:+.2f}</td><td>{v["z"]["capital"]:+.1f}</td>'
        f'<td>{signed(v.get("persistence"))}</td>'
        f'<td class="l mut">{esc(", ".join(t["name"][:8] for t in v["top"][:3]))}</td></tr>'
        for v in kor["groups"][:6])

    def coverage_row(value):
        coverage = value.get("coverage", {})
        return_values = list(value.get("return_coverage", {}).values())
        return_coverage = min(return_values) if return_values else None
        return (
            f'<tr><td class="l">{value["group"]}</td>'
            f'<td class="l">{esc(SECTOR.get(value["sector"],"?"))}</td>'
            + "".join(
                f'<td>{pct(coverage.get(key), 0, sign=False)}</td>'
                for key in F if key != "capital"
            )
            + f'<td>{pct(return_coverage, 0, sign=False)}</td></tr>'
        )

    covrows = "".join(coverage_row(value) for value in g[:8])

    context = (context_payload or {}).get("bottleneck_context", context_payload or {})
    basis = context.get("bottleneck_basis", {})
    context_matches = context.get("group_code") == best["group"]
    basis_verified = bool(context_matches and context.get("candidate_pool_passed"))
    if basis_verified:
        source_rows = []
        for source in basis.get("sources", []):
            title = esc(source.get("title", "출처"))
            observed = esc(source.get("observed_at") or source.get("source_observed_at") or "-")
            if source.get("url"):
                label = f'<a href="{esc(source["url"])}">{title}</a>'
            else:
                label = f'{title}: <code>{esc(json.dumps(source.get("source_locator"), ensure_ascii=False))}</code>'
            source_rows.append(f"<li>{label} · 확인일 {observed}</li>")
        basis_block = f"""
<h2>병목 실체 검증</h2>
<div class="note"><b>통과</b> · {esc(context["group_code"])} 그룹의 정량 점수와 질적 근거가 연결됐다.</div>
<p><b>공급 제약</b> · {esc(basis["constraint"])}</p>
<p><b>지속 기간</b> · {esc(basis["duration"])} ({basis["duration_years"]:g}년)</p>
<p><b>통제 주체</b> · {esc(basis["controller"])}</p>
<ul>{''.join(source_rows)}</ul>"""
    else:
        missing = ", ".join(basis.get("missing", [])) or "검증된 bottleneck_context"
        if context and not context_matches:
            missing = f"최상위 그룹 {best['group']}과 문맥 그룹 {context.get('group_code')}이 다르다"
        basis_block = f"""
<h2>병목 실체 검증</h2>
<div class="note"><b>미검증</b> · {esc(missing)}</div>
<p>공급 제약, 3년을 넘는 지속 기간, 통제 주체와 확인일이 있는 출처를 검증하기 전에는
종목 후보 단계로 넘기지 않는다.</p>"""

    return page(f"섹터 병목 점수 {asof}", f"""
<h1>섹터 병목 점수</h1>
<div class="sub">기준일 {esc(asof)} · 미국 {len(usa['groups'])}개 산업 그룹 ·
원자료 <code>reports/universe-USA-{asof.replace('-','')}.json</code></div>

<div class="verdict"><div class="vgrid">
<div><div class="vk">최상위 병목</div>
<div class="vv">{best["group"]} {esc(SECTOR.get(best["sector"],""))}</div>
<div class="vn">{esc(", ".join(t["t"] for t in best["top"][:4]))}</div></div>
<div><div class="vk">병목 점수</div><div class="vv">{best["score"]:+.2f}</div>
<div class="vn">2위와 {best["score"]-usa["groups"][1]["score"]:+.2f} 차이</div></div>
<div><div class="vk">매출 성장</div>
<div class="vv">{best["raw"]["demand"]*100:.1f}%</div>
<div class="vn">시가총액 가중</div></div>
<div><div class="vk">마진 변화</div>
<div class="vv">{(best["raw"]["pricing"] or 0)*100:+.1f}%p</div>
<div class="vn">가격결정력의 증거</div></div>
</div></div>

<h2>병목을 무엇으로 재는가</h2>
<p>병목이란 수요가 공급을 초과해 그 구간이 가치사슬 전체의 처리량을 제한하는 상태다.
병목 구간은 가격결정력을 쥐고 초과이윤을 가져간다. 텐베거는 여기서 나온다.</p>
<p>다섯 팩터를 산업 그룹 사이에서 표준점수로 바꾸고 가중합한다.
이상치가 표준점수를 무너뜨리므로 양 끝 2%를 절단한 뒤 계산한다.
집계는 시가총액 가중으로 한다.</p>
<div class="verdict"><div class="vgrid">{cards}</div></div>

<h2>산업 그룹 순위</h2>
<div class="scroll"><table>
<thead><tr><th class="l">그룹</th><th class="l">섹터</th><th>점수</th>{fh}
<th>매출성장</th><th>마진변화</th><th>분산</th><th>지속성</th>
<th>시총</th><th class="l">대표 종목</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="mut">팩터 열은 표준점수다. 0이 전체 평균이고 1이면 표준편차 하나만큼 위다.</p>

<h2>데이터 커버리지</h2>
<p>기간 수익률 결측은 0으로 메우지 않는다. 기간별 결측은 {missing_text}다.
각 팩터는 관측 가능한 종목 비율만큼 표준점수를 수축한다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">그룹</th><th class="l">섹터</th>
<th>수요</th><th>가격</th><th>여지</th><th>분산</th><th>수익률</th></tr></thead>
<tbody>{covrows}</tbody></table></div>

<h2>최상위 병목의 기간별 초과수익</h2>
<p>시장 전체 대비 초과수익이다. 여러 기간에 걸쳐 양수면 테마가 아니라 구조다.
지속성은 {signed(best.get("persistence"))}다.</p>
<div class="scroll"><table><thead><tr>{exh}</tr></thead>
<tbody><tr>{exr}</tr></tbody></table></div>

<h2>한국 시장</h2>
<div class="note"><b>점수를 그대로 믿지 않는다.</b>
한국 종목의 컨센서스 추정 보유율이 26%다. 수요와 가격결정력 팩터가 대부분 결측이라
자금 집중과 지속성만 참고한다. 시가총액도 원화라 달러 기준 시총 상한을 그대로 쓰지 못한다.</div>
<div class="scroll"><table>
<thead><tr><th class="l">그룹</th><th class="l">섹터</th><th>점수</th>
<th>자금 집중</th><th>지속성</th><th class="l">대표 종목</th></tr></thead>
<tbody>{krows}</tbody></table></div>

{basis_block}

<footer>재현: <code>python3 scripts/bottleneck.py reports/universe-USA-{asof.replace('-','')}.json</code><br>
투자 판단의 근거 자료이며 매매 권유가 아니다.</footer>""")


# ────────────────────── 기업 리포트 ──────────────────────

def _judge_block(title, j, P, why):
    """판정 하나를 카드 묶음으로 낸다."""
    return f"""<h3>{esc(title)}</h3>
<p class="mut">{esc(why)}</p>
<div class="verdict"><div class="vgrid">
<div><div class="vk">적정가</div><div class="vv">${j["fair"]:,.2f}</div>
<div class="vn">{pct(j["upside"])}</div></div>
<div><div class="vk">상방</div><div class="vv up">${j["high"]:,.2f}</div>
<div class="vn">{pct(j["up"], 0)}</div></div>
<div><div class="vk">하방</div><div class="vv dn">${j["low"]:,.2f}</div>
<div class="vn">{pct(j["down"], 0)}</div></div>
<div><div class="vk">손익비</div><div class="vv">{j["risk_reward"]:.2f} : 1</div>
<div class="vn">{esc(j["call"])}</div></div>
<div><div class="vk">진입가 (2:1)</div>
<div class="vv">${j["entry"]["2:1"]:,.2f}</div>
<div class="vn">{pct(j["entry"]["2:1"]/P-1, 0)}</div></div>
</div></div>"""


def render_company(payload):
    envelope = payload if "valuation" in payload else None
    v = envelope["valuation"] if envelope else payload
    m, t, rev = v["market"], v["tenbagger"], v["reverse"]
    a, rl, gap = v["absolute"], v["relative"], v["disagreement"]
    chk, P = v["consensus_check"], v["market"]["price"]
    f = v.get("fundamentals", {})
    base = v["scenarios"]["기본"]["rows"]
    n_years = len(base)
    y0 = t["final_year"] - t["years"] + 1
    relative_year = v.get("relative_multiple_year", 2027)
    relative_fields = v.get("relative_fields", {
        "sales": f"es{relative_year % 100:02d}",
        "ebitda": f"ee{relative_year % 100:02d}",
        "per": f"per{relative_year % 100:02d}",
    })
    if envelope:
        candidate_label = envelope.get("candidate_status", "reference_only")
        candidate_reasons = envelope.get("candidate_status_reasons", [])
        bottleneck_context = envelope.get("bottleneck_context", {})
    else:
        candidate = v.get("candidate", {})
        candidate_label = "candidate" if candidate.get("eligible") else "reference_only"
        candidate_reasons = candidate.get("reasons", [])
        bottleneck_context = {}
    reason_items = "".join(f"<li>{esc(reason)}</li>" for reason in candidate_reasons)
    context_note = ""
    if bottleneck_context:
        context_note = (
            f'<p>산업 그룹 <code>{esc(bottleneck_context.get("group_code"))}</code> · '
            f'병목 순위 {esc(bottleneck_context.get("rank"))}위 · '
            f'근거 검증 {"통과" if bottleneck_context.get("candidate_pool_passed") else "미통과"}</p>'
        )
    candidate_block = f"""
<div class="note"><b>후보 상태: {esc(candidate_label)}</b>{context_note}
{'<ul>' + reason_items + '</ul>' if reason_items else '<p>병목과 가치평가 안전장치를 통과했다.</p>'}</div>"""

    provenance = v.get("data_provenance", {})
    provenance_links = " · ".join(
        f'<a href="{esc(url)}">출처</a>' for url in provenance.get("source_urls", [])
    ) or "출처 URL 없음"
    provenance_block = f"""
<h2>현재 데이터 출처</h2>
<p>제공자 {esc(provenance.get("provider", "-"))} · 조회 시점 {esc(provenance.get("queried_at", "-"))} ·
상태 {esc(provenance.get("status", "-"))} · {provenance_links}</p>"""
    special = v.get("special_situation", {})
    special_block = ""
    if special.get("active"):
        special_block = f"""
<h2>특수 상황</h2>
<div class="note"><b>{esc(special.get("type", "미분류"))}</b> ·
검토 {esc(special.get("review_status", "미완료"))} · 결정 {esc(special.get("decision", "미정"))}</div>"""
    sales_field = relative_fields["sales"]
    ebitda_field = relative_fields["ebitda"]
    per_field = relative_fields["per"]
    multiple_labels = {
        sales_field: "EV/Sales",
        ebitda_field: "EV/EBITDA",
        per_field: "선행 PER",
    }

    srows = ""
    for name, s in v["scenarios"].items():
        srows += (f'<tr><td class="l"><b>{esc(name)}</b></td><td>{s["p"]*100:.0f}%</td>'
                  f'<td>${s["ps"]:,.2f}</td><td>{pct(s["upside"])}</td>'
                  f'<td>{s["tv_share"]*100:.0f}%</td>'
                  f'<td>{num(s["rows"][-1]["rev"],0)}</td>'
                  f'<td>{s["rows"][-1]["opm"]*100:.1f}%</td></tr>')

    fyrows = "".join(
        f'<tr><td class="l">{y0+i}년</td><td>{num(r["rev"],0)}</td>'
        f'<td>{r["opm"]*100:.1f}%</td><td>{num(r["nopat"],0)}</td>'
        f'<td>{num(r["sbc"],0)}</td><td>{num(r["dnwc"],0)}</td>'
        f'<td><b>{num(r["fcf"],0)}</b></td></tr>' for i, r in enumerate(base))

    mrows = ""
    for k, fit in v["multiple_fits"].items():
        lbl = multiple_labels[k]
        ok = "외삽 — 회귀를 쓰지 않는다" if fit["extrapolates"] else "사용 가능"
        cls = "dn" if fit["extrapolates"] else "up"
        mrows += (f'<tr><td class="l">{lbl}</td><td>{fit["r2"]:.2f}</td>'
                  f'<td>{fit["xmin"]*100:.1f}% ~ {fit["xmax"]*100:.1f}%</td>'
                  f'<td>{v["target_growth"]*100:.0f}%</td>'
                  f'<td class="l {cls}">{ok}</td></tr>')
    if not mrows:
        mrows = '<tr><td colspan="5" class="l mut">상대가치 보류</td></tr>'

    rrows = "".join(
        f'<tr><td class="l">{esc(r["multiple"])}</td><td class="l">{esc(r["basis"])}</td>'
        f'<td>{r["mult"]:.1f}배</td><td>${r["price"]:,.2f}</td>'
        f'<td>{pct(r["upside"])}</td></tr>' for r in v["relative_rows"])
    if not rrows:
        rrows = '<tr><td colspan="5" class="l mut">상대가치 보류</td></tr>'

    prows = ""
    for tk, p in sorted(v["peers"].items(), key=lambda kv: -(kv[1].get("mcap") or 0)):
        if not p.get(sales_field):
            continue
        hi = ' class="hi"' if tk == v["ticker"] else ""
        prows += (f'<tr{hi}><td class="l">{esc(tk)}</td><td>{num(p["mcap"]/1000,0)}B</td>'
                  f'<td>{num(p[sales_field])}</td><td>{num(p.get(ebitda_field))}</td>'
                  f'<td>{num(p.get(per_field))}</td><td>{pct(p.get("rev_g"))}</td></tr>')
    if not prows:
        prows = '<tr><td colspan="6" class="l mut">상대가치 기준연도 배수가 없다.</td></tr>'

    trows = "".join(
        f'<tr><td class="l"><b>{esc(nm)}</b></td><td>{r["p"]*100:.0f}%</td>'
        f'<td>{num(r["revenue_end"],0)}</td><td>{r["ev_sales_end"]:.1f}배</td>'
        f'<td>${r["ps_end"]:,.2f}</td><td>{r["multiple"]:.1f}배</td>'
        f'<td>{pct(r["cagr"])}</td></tr>' for nm, r in t["scenarios"].items())

    A = v.get("assumptions", {})
    arows = "".join(
        f'<tr><td class="l"><b>{esc(k)}</b></td><td>{x["wacc"]*100:.1f}%</td>'
        f'<td>{x["g"]*100:.1f}%</td><td>{x["tax"]*100:.0f}%</td>'
        f'<td class="l mut">{esc(" · ".join(x["revenue_source"]))}</td></tr>'
        for k, x in A.items())
    ratl = "".join(f'<p><b>{esc(k)}</b> — {esc(x["rationale"])}</p>'
                   for k, x in A.items() if x.get("rationale"))
    tamrow = ""
    if t.get("tam_share_needed"):
        tamrow = (f'<p>기말 매출 {t["terminal_revenue"]:,.0f} 백만 달러는 '
                  f'{t["tam_year"]}년 시장 {t["tam"]:,.0f} 백만 달러의 '
                  f'<b>{t["tam_share_needed"]*100:.0f}%</b>다.</p>')
    rel_hold = v.get("relative_hold_reason") or "상대가치 기준연도 배수가 부족하다."
    relative_block = (_judge_block("상대가치 (동종 배수)", rl, P,
                      "시장이 같은 부류에 매기는 값이다. 그 배수 자체가 옳은지는 묻지 않는다.")
                      if rl else
                      f'<div class="note"><b>상대가치 보류</b> — {esc(rel_hold)}</div>')
    gap_block = (f'<div class="note"><b>두 방법의 차이 {gap["gap"]*100:+.1f}%</b> — '
                 f'{esc(gap["note"])}</div>' if gap else
                 f'<div class="note"><b>두 방법의 차이 보류</b> — {esc(rel_hold)}</div>')
    if chk["consensus_sales"] is None:
        consensus_note = (f'<div class="note"><b>컨센서스를 역산하지 못했다.</b> '
                          f'회사 가이던스는 {chk["guidance_sales"]:,.0f} 백만 달러다. '
                          f'{esc(chk.get("reason", ""))} 가이던스로 교체해 계산했다.</div>')
    else:
        consensus_note = (f'<div class="note"><b>{"컨센서스가 갱신되지 않았다." if chk["stale"] else "컨센서스가 가이던스와 맞는다."}</b> '
                          f'데이터 제공자의 매출 추정은 {chk["consensus_sales"]:,.0f} 백만 달러이고 '
                          f'회사 가이던스는 {chk["guidance_sales"]:,.0f} 백만 달러다. 괴리가 {chk["gap"]*100:+.1f}%다. '
                          f'{"가이던스로 교체해 계산했다." if chk["stale"] else ""}</div>')

    return page(f'{v["name"]} 밸류에이션 {v["asof"]}', f"""
<h1>{esc(v["name"])} <span class="mut">({esc(v["ticker"])})</span></h1>
<div class="sub">기준일 {esc(v["asof"])} · 현재가 ${P:,.2f} ·
시가총액 {P*m["shares"]/100:,.0f}억 달러 ·
재현 <code>python3 scripts/valuation.py {esc(v["ticker"])}</code></div>

{candidate_block}

<div class="note"><b>두 밸류에이션을 합치지 않는다.</b>
절대가치는 이 사업이 벌어들일 현금의 오늘 값을 묻고,
상대가치는 시장이 같은 부류에 매기는 값을 묻는다.
서로 다른 질문이라 가중평균은 어느 질문에도 답하지 못한다.
두 답이 갈리면 그 차이 자체가 결론이다.</div>

<h2>판정</h2>
{_judge_block("절대가치 (DCF)", a, P,
  "이 사업의 현금흐름만 보고 매긴 값이다. 시장이 어떻게 보든 무관하다.")}
{relative_block}

{gap_block}

<h2>{t["years"]}년 뒤와 텐베거</h2>
<p>{t["years"]}년 안에 10배가 되려면 연복리 {t["required_cagr"]*100:.0f}%가 필요하다.
매출과 배수가 함께 폭증해야 나오는 값이라 결과가 크게 갈리는 기업에서만 가능하다.
아래는 배수를 고정하지 않고 {t["final_year"]}년 시점의 기업가치를 직접 구한 값이다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">시나리오</th><th>확률</th><th>{t["final_year"]}년 매출</th>
<th>그때 EV/Sales</th><th>기말 주당</th><th>배수</th><th>연복리</th></tr></thead>
<tbody>{trows}
<tr class="hi"><td class="l"><b>확률가중</b></td><td>100%</td><td colspan="3"></td>
<td><b>{t["weighted_multiple"]:.1f}배</b></td>
<td>{pct(t["weighted_cagr"])}</td></tr></tbody></table></div>
<p><b>진폭 {t["spread"]:.1f}배</b> — 최선과 최악의 비율이다.
최선은 {esc(t["best_scenario"])} 시나리오의 {t["best_multiple"]:.1f}배이고
그 확률은 {t["best_probability"]*100:.0f}%다.
진폭이 클수록 단기 텐베거 여지가 있고, 동시에 잃을 폭도 크다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">항</th><th>배수</th><th class="l">내용</th></tr></thead>
<tbody>
<tr><td class="l">매출</td><td>{t["revenue_multiple"]:.1f}배</td>
<td class="l mut">{t["final_year"]}년 매출 ÷ 직전 실적</td></tr>
<tr><td class="l">이익률</td><td>{t["margin_multiple"]:.2f}배</td>
<td class="l mut">기말 영업이익률 ÷ 현재 영업이익률</td></tr>
<tr><td class="l">배수</td><td class="dn">{t["rerating"]:.2f}배</td>
<td class="l mut">EV/Sales {t["ev_sales_now"]:.1f} → {t["ev_sales_end"]:.1f}</td></tr>
</tbody></table></div>
{tamrow}
<div class="note"><b>판정: {esc(t["verdict"][0])}</b> — {esc(t["verdict"][1])}</div>

<h2>컨센서스 검증</h2>
{consensus_note}

<h2>절대가치 상세</h2>
<p>명시 예측 {n_years}년에 잔존가치를 더한다.
명시 기간이 짧아 잔존가치 비중이 커지므로 영구성장률을 미국 장기 명목 GDP 성장률보다
낮게 잡아 그것을 상쇄한다.
자유현금흐름은 <code>매출 × 영업이익률 × (1 − 세율) − SBC − 운전자본 증가분</code>으로 잡았다.
주식보상비용은 주주가 실제로 부담하는 비용이므로 차감한다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">시나리오</th><th>확률</th><th>주당가치</th><th>현재가 대비</th>
<th>잔존가치 비중</th><th>기말 매출</th><th>기말 영업이익률</th></tr></thead>
<tbody>{srows}
<tr class="hi"><td class="l"><b>확률가중</b></td><td>100%</td>
<td><b>${a["fair"]:,.2f}</b></td><td>{pct(a["upside"])}</td>
<td colspan="3"></td></tr></tbody></table></div>

<h3>시나리오 가정과 근거</h3>
<div class="scroll"><table>
<thead><tr><th class="l">시나리오</th><th>WACC</th><th>영구성장률</th><th>세율</th>
<th class="l">매출 추정 출처</th></tr></thead>
<tbody>{arows}</tbody></table></div>
{ratl}
<p class="mut"><b>확률의 근거</b> — {esc(v.get("probability_basis",""))}</p>

{provenance_block}
{special_block}

<h3>기본 시나리오 현금흐름 (백만 달러)</h3>
<div class="scroll"><table>
<thead><tr><th class="l">연도</th><th>매출</th><th>영업이익률</th><th>세후영업이익</th>
<th>주식보상</th><th>운전자본</th><th>자유현금흐름</th></tr></thead>
<tbody>{fyrows}</tbody></table></div>

<h3>역DCF: 현재 주가가 전제하는 것</h3>
<p>넷 중 하나만 성립하면 현재 주가가 정당화된다.
넷 다 현실 범위 밖이면 시장이 과열이고, 하나라도 가능하면 내 가정을 의심해야 한다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">무엇을 바꾸면</th><th>필요한 값</th><th class="l">비교</th></tr></thead>
<tbody>
<tr><td class="l">할인율</td><td>{rev["implied_wacc"]*100:.2f}%</td>
<td class="l mut">내가 쓴 WACC {v["assumptions"]["기본"]["wacc"]*100:.1f}%</td></tr>
<tr><td class="l">{rev["years"]}년 매출 연복리</td><td>{rev["implied_cagr"]*100:.1f}%</td>
<td class="l mut">기말 매출 {rev["implied_terminal_revenue"]:,.0f} 백만 달러</td></tr>
<tr><td class="l">영구성장률</td><td>{rev["implied_g"]*100:.2f}%</td>
<td class="l mut">미국 장기 명목 GDP 성장률 약 4%</td></tr>
<tr><td class="l">영업이익률</td><td>{rev["implied_opm"]*100:.1f}%</td>
<td class="l mut">업계 최고 수준이 약 62%</td></tr>
</tbody></table></div>

<h2>상대가치 상세</h2>
<h3>어떤 배수를 쓸지 데이터로 판정한다</h3>
<p>손으로 고르지 않는다. 동종군에서 각 배수가 성장률로 설명되는 정도를 회귀로 재고,
대상 종목의 성장률이 동종군 범위 밖이면 그 회귀를 버린다.</p>
<p class="mut">상대가치 기준 연도는 {relative_year}년이다.
배수 필드는 <code>{esc(sales_field)}</code>, <code>{esc(ebitda_field)}</code>,
<code>{esc(per_field)}</code> 를 쓴다.</p>
<div class="scroll"><table>
<thead><tr><th class="l">배수</th><th>결정계수</th><th>적합 성장률 구간</th>
<th>대상 성장률</th><th class="l">판정</th></tr></thead>
<tbody>{mrows}</tbody></table></div>
<p class="mut">LTM PER 과 PBR 은 계산에서 제외했다.
인수 무형자산 상각이 GAAP 순이익과 장부가를 함께 왜곡한다.</p>

<h3>동종군 사분위</h3>
<div class="scroll"><table>
<thead><tr><th class="l">배수</th><th class="l">기준</th><th>배수값</th>
<th>주당가치</th><th>현재가 대비</th></tr></thead>
<tbody>{rrows}</tbody></table></div>

<h3>비교군</h3>
<div class="scroll"><table>
<thead><tr><th class="l">종목</th><th>시총</th><th>EV/Sales</th>
<th>EV/EBITDA</th><th>선행 PER</th><th>매출성장</th></tr></thead>
<tbody>{prows}</tbody></table></div>

<footer>모든 숫자는 <code>scripts/valuation.py</code> 출력에서 나왔다.
가정은 <code>scripts/inputs/{esc(v["ticker"])}.json</code> 에 있다.<br>
투자 판단의 근거 자료이며 매매 권유가 아니다.</footer>""")


def main():
    a = sys.argv[1:]
    if not a or a[0] in {"-h", "--help"}:
        print(__doc__.strip())
        raise SystemExit(0)
    if "-o" not in a:
        print(__doc__.strip(), file=sys.stderr)
        print("\n오류: 출력 경로를 '-o <출력>' 형식으로 지정해야 한다.", file=sys.stderr)
        raise SystemExit(2)
    out_i = a.index("-o")
    if out_i == len(a) - 1:
        print(__doc__.strip(), file=sys.stderr)
        print("\n오류: '-o' 뒤에 출력 경로가 없다.", file=sys.stderr)
        raise SystemExit(2)
    before_output = list(a[:out_i])
    context_path = None
    if "--context" in before_output:
        context_i = before_output.index("--context")
        if context_i == len(before_output) - 1:
            print("\n오류: '--context' 뒤에 입력 JSON 경로가 없다.", file=sys.stderr)
            raise SystemExit(2)
        context_path = before_output[context_i + 1]
        del before_output[context_i:context_i + 2]
    kind = before_output[0]
    if kind not in {"bottleneck", "company"}:
        print(__doc__.strip(), file=sys.stderr)
        print(f"\n오류: 알 수 없는 리포트 종류다: {kind}", file=sys.stderr)
        raise SystemExit(2)
    if kind == "company" and len(before_output) != 2:
        print(__doc__.strip(), file=sys.stderr)
        print("\n오류: company 리포트는 입력 JSON 하나가 필요하다.", file=sys.stderr)
        raise SystemExit(2)
    if kind == "bottleneck" and len(before_output) < 3:
        print(__doc__.strip(), file=sys.stderr)
        print("\n오류: bottleneck 리포트는 미국 JSON 과 한국 JSON 이 필요하다.", file=sys.stderr)
        raise SystemExit(2)
    out = a[out_i + 1]
    if kind == "bottleneck":
        usa = json.loads(Path(before_output[1]).read_text())
        kor = json.loads(Path(before_output[2]).read_text())
        asof = before_output[3] if len(before_output) > 3 else "2026-08-28"
        context_payload = json.loads(Path(context_path).read_text()) if context_path else None
        Path(out).write_text(render_bottleneck(usa, kor, asof, context_payload))
    else:
        v = json.loads(Path(before_output[1]).read_text())
        Path(out).write_text(render_company(v))
    print(f"작성: {out}")


if __name__ == "__main__":
    main()
