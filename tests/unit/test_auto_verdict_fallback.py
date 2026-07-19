from __future__ import annotations

from core.utils.auto_verdict_fallback import build_auto_verdict_fallback_text


def _sample_report() -> dict[str, object]:
    return {
        "account": {
            "id": "acc-1",
            "account_id": "123",
            "name": "Main account",
            "currency": "USD",
            "timezone_name": "Asia/Almaty",
        },
        "periods": {
            "current": {"since": "2026-06-01", "until": "2026-06-30"},
            "previous": {"since": "2026-05-01", "until": "2026-05-31"},
        },
        "summary": {
            "primary_result_kind": "leads",
            "metrics": {
                "spend": {"current": 120.0, "previous": 100.0, "delta_pct": 20.0},
                "reach": {"current": 1000, "previous": 900, "delta_pct": 11.1},
                "impressions": {"current": 1500, "previous": 1400, "delta_pct": 7.1},
                "clicks": {"current": 120, "previous": 100, "delta_pct": 20.0},
                "ctr": {"current": 8.0, "previous": 7.0, "delta_pct": 14.3},
                "cpm": {"current": 10.0, "previous": 9.0, "delta_pct": 11.1},
                "cpc": {"current": 1.0, "previous": 1.0, "delta_pct": 0.0},
                "results": {"current": 10, "previous": 8, "delta_pct": 25.0},
                "cost_per_result": {"current": 12.0, "previous": 12.5, "delta_pct": -4.0},
            },
            "active_campaigns": 2,
            "total_campaigns": 2,
        },
        "campaigns": [
            {
                "id": "cmp-1",
                "name": "Lead Gen Core",
                "status": "ACTIVE",
                "primary_result_kind": "leads",
                "metrics": {
                    "spend": {"current": 60.0, "previous": 45.0, "delta_pct": 33.3},
                    "results": {"current": 7, "previous": 5, "delta_pct": 40.0},
                    "cost_per_result": {"current": 8.57, "previous": 9.0, "delta_pct": -4.8},
                },
                "creatives": [],
            },
            {
                "id": "cmp-2",
                "name": "Retargeting Warm",
                "status": "ACTIVE",
                "primary_result_kind": "leads",
                "metrics": {
                    "spend": {"current": 60.0, "previous": 55.0, "delta_pct": 9.1},
                    "results": {"current": 3, "previous": 3, "delta_pct": 0.0},
                    "cost_per_result": {"current": 20.0, "previous": 18.33, "delta_pct": 9.1},
                },
                "creatives": [],
            },
        ],
    }


def test_build_auto_verdict_fallback_text_highlights_best_and_risk_campaigns():
    text = build_auto_verdict_fallback_text(_sample_report(), language="ru")

    assert "Серверный AI-ответ временно недоступен" in text
    assert "Lead Gen Core" in text
    assert "Retargeting Warm" in text
    assert "Следующий шаг: сместить часть бюджета из Retargeting Warm в Lead Gen Core" in text
    assert "- Активно кампаний: 2 из 2." in text
    assert "- Лидер: Lead Gen Core" in text
    assert "- Зона внимания: Retargeting Warm" in text
