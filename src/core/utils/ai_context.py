from __future__ import annotations


def build_report_context(report: dict[str, object]) -> str:
    account = report["account"]
    summary = report["summary"]
    metrics = summary["metrics"]
    campaigns = report["campaigns"]

    lines = [
        f"Account: {account['name']} ({account['account_id']})",
        f"Current period: {report['periods']['current']['since']} to {report['periods']['current']['until']}",
        f"Previous period: {report['periods']['previous']['since']} to {report['periods']['previous']['until']}",
        "",
        "Summary:",
        f"- Spend: {metrics['spend']['current']}",
        f"- Reach: {metrics['reach']['current']}",
        f"- Impressions: {metrics['impressions']['current']}",
        f"- Clicks: {metrics['clicks']['current']}",
        f"- CTR: {metrics['ctr']['current']}",
        f"- CPM: {metrics['cpm']['current']}",
        f"- CPC: {metrics['cpc']['current']}",
        f"- Primary result kind: {summary['primary_result_kind']}",
        f"- Results: {metrics['results']['current']}",
        f"- Cost per result: {metrics['cost_per_result']['current']}",
        "",
        "Campaigns:",
    ]

    for campaign in campaigns:
        campaign_metrics = campaign["metrics"]
        lines.append(
            f"- {campaign['name']} [{campaign['status']}]: spend={campaign_metrics['spend']['current']}, "
            f"impressions={campaign_metrics['impressions']['current']}, "
            f"clicks={campaign_metrics['clicks']['current']}, ctr={campaign_metrics['ctr']['current']}, "
            f"results={campaign_metrics['results']['current']} ({campaign['primary_result_kind']})"
        )
        for creative in campaign["creatives"][:5]:
            creative_metrics = creative["metrics"]
            lines.append(
                f"  * Creative {creative['name']}: spend={creative_metrics['spend']}, "
                f"impressions={creative_metrics['impressions']}, clicks={creative_metrics['clicks']}, "
                f"ctr={creative_metrics['ctr']}, results={creative_metrics['results']} ({creative_metrics['result_kind']})"
            )

    return "\n".join(lines)
