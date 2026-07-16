from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import server
from import_tracking_workbook import stable_source_id, valid_record_code, workbook_rows


def unique_index(rows: list[dict], key_builder) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        key = key_builder(row)
        if key and key != ("", ""):
            grouped[key].append(row)
    return {key: values[0] for key, values in grouped.items() if len(values) == 1}


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair filing dates from Excel section headers.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    _, workbook_leads, _ = workbook_rows(args.workbook, args.year)
    dated_rows = [row for row in workbook_leads if row.get("recordDate")]
    config = server.load_config()
    sales = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'sourceId',`source_project_id`,"
        "'projectName',`company_name`,'projectCompany',`project_unit`,'recordCode',`credit_code`) "
        "FROM `sales_leads` WHERE `source`='Excel整理表' AND COALESCE(`record_date`,'')=''",
        config,
    )
    filings = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'projectName',`project_name`,"
        "'projectCompany',`project_unit`,'recordCode',`project_code`) "
        "FROM `filing_projects` WHERE `source` LIKE 'Excel%' AND COALESCE(`record_date`,'')=''",
        config,
    )

    sales_by_source = unique_index(sales, lambda row: str(row.get("sourceId") or "").strip())
    sales_by_code = unique_index(sales, lambda row: str(row.get("recordCode") or "").strip() if valid_record_code(str(row.get("recordCode") or "")) else "")
    sales_by_pair = unique_index(sales, lambda row: (str(row.get("projectName") or "").strip(), str(row.get("projectCompany") or "").strip()))
    filing_by_code = unique_index(filings, lambda row: str(row.get("recordCode") or "").strip() if valid_record_code(str(row.get("recordCode") or "")) else "")
    filing_by_pair = unique_index(filings, lambda row: (str(row.get("projectName") or "").strip(), str(row.get("projectCompany") or "").strip()))

    sales_updates = {}
    filing_updates = {}
    for row in dated_rows:
        project_name = str(row.get("projectName") or "").strip()
        project_company = str(row.get("projectCompany") or "").strip()
        record_code = str(row.get("recordCode") or "").strip()
        source_id = stable_source_id("target", project_name, project_company, record_code)
        sales_match = sales_by_source.get(source_id)
        if not sales_match and valid_record_code(record_code):
            sales_match = sales_by_code.get(record_code)
        sales_match = sales_match or sales_by_pair.get((project_name, project_company))
        if sales_match:
            sales_updates[int(sales_match["id"])] = row["recordDate"]

        filing_match = filing_by_code.get(record_code) if valid_record_code(record_code) else None
        filing_match = filing_match or filing_by_pair.get((project_name, project_company))
        if filing_match:
            filing_updates[int(filing_match["id"])] = row["recordDate"]

    marker_rows = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR)) FROM `sales_leads` "
        "WHERE `source`='Excel整理表' AND COALESCE(`record_date`,'')='' AND COALESCE(`project_unit`,'')='' "
        "AND COALESCE(`credit_code`,'')='' AND (`company_name` REGEXP '^[0-9]{1,2}[.]?[0-9]{1,2}$' "
        "OR `company_name` REGEXP '^4[0-9]{4}$')",
        config,
    )

    summary = {
        "workbookDatedRows": len(dated_rows),
        "salesDatesResolved": len(sales_updates),
        "filingDatesResolved": len(filing_updates),
        "dateHeadingRows": len(marker_rows),
        "mode": "apply" if args.apply else "dry-run",
    }
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    sales_backup = f"sales_leads_backup_{suffix}_sectiondate"
    filing_backup = f"filing_projects_backup_{suffix}_sectiondate"
    server.run_mysql(
        f"CREATE TABLE {server.quote_identifier(sales_backup)} LIKE `sales_leads`;"
        f"INSERT INTO {server.quote_identifier(sales_backup)} SELECT * FROM `sales_leads`;"
        f"CREATE TABLE {server.quote_identifier(filing_backup)} LIKE `filing_projects`;"
        f"INSERT INTO {server.quote_identifier(filing_backup)} SELECT * FROM `filing_projects`;",
        config,
    )
    statements = [
        f"UPDATE `sales_leads` SET `record_date`={server.sql_literal(date_text)} WHERE `id`={row_id} AND COALESCE(`record_date`,'')='' LIMIT 1;"
        for row_id, date_text in sales_updates.items()
    ]
    statements.extend(
        f"UPDATE `filing_projects` SET `record_date`={server.sql_literal(date_text)} WHERE `id`={row_id} AND COALESCE(`record_date`,'')='' LIMIT 1;"
        for row_id, date_text in filing_updates.items()
    )
    statements.extend(
        f"UPDATE `sales_leads` SET `source`='Excel日期分组' WHERE `id`={int(row['id'])} LIMIT 1;"
        for row in marker_rows
    )
    for start in range(0, len(statements), 80):
        server.run_mysql("START TRANSACTION;" + "".join(statements[start:start + 80]) + "COMMIT;", config)
    summary.update({"salesBackup": sales_backup, "filingBackup": filing_backup})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
