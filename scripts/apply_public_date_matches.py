from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server


def filing_month(record_code: str) -> str:
    matched = re.fullmatch(r"(\d{2})(\d{2})-\d{6}-\d{2}-\d{2}-\d{6}", str(record_code or "").strip())
    if not matched:
        return ""
    return f"20{matched.group(1)}-{matched.group(2)}"


def validate_match(match: dict, database_row: dict) -> str:
    expected = {
        "projectName": "company_name",
        "projectCompany": "project_unit",
        "recordCode": "credit_code",
    }
    for key, column in expected.items():
        if str(match.get(key) or "").strip() != str(database_row.get(column) or "").strip():
            return f"{key} 与数据库不一致"
    date_text = str(match.get("recordDate") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
        return "recordDate 格式无效"
    code_month = filing_month(match.get("recordCode", ""))
    if code_month and not date_text.startswith(code_month):
        return "公开日期月份与备案号月份不一致"
    if str(database_row.get("record_date") or "").strip():
        return "数据库已有日期"
    if str(match.get("confidence") or "") != "high":
        return "仅允许 high 置信度自动写入"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply audited public filing-date matches to undated sales leads.")
    parser.add_argument("matches", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    matches = json.loads(args.matches.read_text(encoding="utf-8"))
    config = server.load_config()
    accepted = []
    rejected = []
    for match in matches:
        lead_id = int(match.get("leadId") or 0)
        rows = server.json_rows(
            "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'company_name',`company_name`,"
            "'project_unit',`project_unit`,'credit_code',`credit_code`,'record_date',`record_date`) "
            f"FROM `sales_leads` WHERE `id`={lead_id} LIMIT 1",
            config,
        )
        reason = "销售线索不存在" if not rows else validate_match(match, rows[0])
        if reason:
            rejected.append({"leadId": lead_id, "reason": reason})
        else:
            accepted.append(match)

    summary = {
        "total": len(matches),
        "accepted": len(accepted),
        "rejected": rejected,
        "mode": "apply" if args.apply else "dry-run",
    }
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"sales_leads_backup_{suffix}_publicdate"
    server.run_mysql(
        f"CREATE TABLE {server.quote_identifier(backup)} LIKE `sales_leads`;"
        f"INSERT INTO {server.quote_identifier(backup)} SELECT * FROM `sales_leads`;"
        "CREATE TABLE IF NOT EXISTS `lead_date_match_audit` ("
        "`id` bigint unsigned NOT NULL AUTO_INCREMENT,`lead_id` bigint unsigned NOT NULL,"
        "`matched_date` varchar(10) NOT NULL,`source_title` varchar(255) NOT NULL DEFAULT '',"
        "`source_url` text NOT NULL,`match_method` varchar(255) NOT NULL DEFAULT '',"
        "`confidence` varchar(32) NOT NULL DEFAULT '',`created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "PRIMARY KEY (`id`),UNIQUE KEY `uq_lead_date_source` (`lead_id`,`matched_date`,`source_title`)) "
        "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
        config,
    )
    statements = []
    for match in accepted:
        lead_id = int(match["leadId"])
        statements.append(
            f"UPDATE `sales_leads` SET `record_date`={server.sql_literal(match['recordDate'])} "
            f"WHERE `id`={lead_id} AND COALESCE(`record_date`,'')='' LIMIT 1;"
        )
        statements.append(
            "INSERT INTO `lead_date_match_audit` "
            "(`lead_id`,`matched_date`,`source_title`,`source_url`,`match_method`,`confidence`) VALUES ("
            f"{lead_id},{server.sql_literal(match['recordDate'])},{server.sql_literal(match['sourceTitle'])},"
            f"{server.sql_literal(match['sourceUrl'])},{server.sql_literal(match['matchMethod'])},"
            f"{server.sql_literal(match['confidence'])}) ON DUPLICATE KEY UPDATE `source_url`=VALUES(`source_url`),"
            "`match_method`=VALUES(`match_method`),`confidence`=VALUES(`confidence`);"
        )
    if statements:
        server.run_mysql("START TRANSACTION;" + "".join(statements) + "COMMIT;", config)
    summary["salesBackup"] = backup
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
