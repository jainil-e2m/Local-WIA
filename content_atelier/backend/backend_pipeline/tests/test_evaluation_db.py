"""E.B2 "done when" on the migrated database: labels for Weeks 1 and 2 (and 3, 4 and the export pairs) are rows, each
recording its source and whether it is a proxy; Week 6 is untouched; seeding twice changes nothing."""
from __future__ import annotations

from backend_pipeline.database import connect
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)
from evaluation import benchmark


def test_the_benchmark_labels_are_calibration_rows(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        first = benchmark.seed(conn)
        again = benchmark.seed(conn)
        rows = conn.execute("SELECT source,proxy,week_id,count(*) AS n FROM calibration_labels GROUP BY 1,2,3 ORDER BY 1,3").fetchall()
    assert first["written"] == first["labels"] == 51 and again["written"] == 0
    found = {(r["source"], r["proxy"], r["week_id"]): r["n"] for r in rows}
    assert found[("whitney_week1_review_2026-10-13", False, "week_2026-06-01")] == 6
    assert found[("chatgpt_review_week2", True, "week_2026-06-08")] == 1
    assert found[("chatgpt_export", True, None)] == 38
    assert sum(n for (source, _, _), n in found.items() if source == "root_cause_2026-10-16") == 6
    assert not any(week == "week_2026-07-06" for (_, _, week) in found), "Week 6 is untouched"


def test_ground_truth_reads_wia_judgements_only_unless_proxies_are_asked_for(platform_url):  # noqa: F811
    """Section 2.3: what calibrates a judge, E.B5 or E.B6 is WIA's own judgement. Proxy labels (ChatGPT's verdicts,
    the export pairs, a decision recorded under D12 by someone outside WIA) stay readable when asked for."""
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        benchmark.seed(conn)
        conn.execute("""INSERT INTO calibration_labels(label_id,item_kind,item_id,disposition,rater,author,source,proxy)
            VALUES ('label_delegated','angle','angle_x','skip','engineer@example.invalid','engineer@example.invalid',
            'gate_delegated',true)""")
        truth = benchmark.ground_truth(conn)
        everything = benchmark.ground_truth(conn, include_proxy=True)
    assert truth and not any(r["proxy"] for r in truth) and {r["source"] for r in truth} == {"whitney_week1_review_2026-10-13"}
    assert len(everything) == 52 and any(r["source"] == "gate_delegated" for r in everything)
