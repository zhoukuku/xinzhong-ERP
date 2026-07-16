from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server


def normalize(value) -> str:
    return str(value or "").strip()


def unique_date_index(rows: list[dict], key_builder) -> dict:
    grouped = defaultdict(set)
    for row in rows:
        key = key_builder(row)
        date_text = normalize(row.get("recordDate"))[:10]
        if key and key != ("", "") and date_text:
            grouped[key].add(date_text)
    return {key: next(iter(dates)) for key, dates in grouped.items() if len(dates) == 1}


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair missing dates from the legacy Shenzhen filing SQLite database.")
    parser.add_argument("database", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    legacy_rows = [
        {
            "projectName": normalize(row["company_name"]),
            "projectCompany": normalize(row["project_unit"]),
            "recordCode": normalize(row["credit_code"]),
            "recordDate": normalize(row["record_date"]),
        }
        for row in connection.execute(
            "SELECT company_name,project_unit,credit_code,record_date FROM companies "
            "WHERE source='深圳投资网' AND COALESCE(record_date,'')<>''"
        )
    ]
    connection.close()

    by_code = unique_date_index(legacy_rows, lambda row: normalize(row.get("recordCode")))
    by_pair = unique_date_index(
        legacy_rows,
        lambda row: (normalize(row.get("projectName")), normalize(row.get("projectCompany"))),
    )
    config = server.load_config()
    undated = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'projectName',`company_name`,"
        "'projectCompany',`project_unit`,'recordCode',`credit_code`) FROM `sales_leads` "
        "WHERE `source`<>'Excel日期分组' AND COALESCE(`record_date`,'')=''",
        config,
    )
    updates = {}
    for row in undated:
        record_code = normalize(row.get("recordCode"))
        pair = (normalize(row.get("projectName")), normalize(row.get("projectCompany")))
        date_text = by_code.get(record_code, "") if record_code else ""
        date_text = date_text or by_pair.get(pair, "")
        if date_text:
            updates[int(row["id"])] = date_text

    summary = {"legacyRows": len(legacy_rows), "salesDatesResolved": len(updates), "mode": "apply" if args.apply else "dry-run"}
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"sales_leads_backup_{suffix}_legacydate"
    server.run_mysql(
        f"CREATE TABLE {server.quote_identifier(backup)} LIKE `sales_leads`;"
        f"INSERT INTO {server.quote_identifier(backup)} SELECT * FROM `sales_leads`;",
        config,
    )
    statements = [
        f"UPDATE `sales_leads` SET `record_date`={server.sql_literal(date_text)} "
        f"WHERE `id`={row_id} AND COALESCE(`record_date`,'')='' LIMIT 1;"
        for row_id, date_text in updates.items()
    ]
    for start in range(0, len(statements), 80):
        server.run_mysql("START TRANSACTION;" + "".join(statements[start:start + 80]) + "COMMIT;", config)
    summary["salesBackup"] = backup
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
