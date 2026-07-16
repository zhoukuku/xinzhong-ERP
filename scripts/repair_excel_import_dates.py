from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server


def unique_date(values: set[str]) -> str:
    clean = {str(value or "")[:10] for value in values if str(value or "").strip()}
    return next(iter(clean)) if len(clean) == 1 else ""


def build_date_indexes(rows: list[dict]) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    code_dates: dict[str, set[str]] = defaultdict(set)
    pair_dates: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        date_text = str(row.get("recordDate") or "")[:10]
        code = str(row.get("recordCode") or "").strip()
        pair = (str(row.get("projectName") or "").strip(), str(row.get("projectCompany") or "").strip())
        if code and date_text:
            code_dates[code].add(date_text)
        if pair != ("", "") and date_text:
            pair_dates[pair].add(date_text)
    return (
        {key: unique_date(values) for key, values in code_dates.items()},
        {key: unique_date(values) for key, values in pair_dates.items()},
    )


def resolved_date(row: dict, by_code: dict[str, str], by_pair: dict[tuple[str, str], str]) -> str:
    code = str(row.get("recordCode") or "").strip()
    pair = (str(row.get("projectName") or "").strip(), str(row.get("projectCompany") or "").strip())
    return by_code.get(code, "") or by_pair.get(pair, "")


def main() -> int:
    config = server.load_config()
    official = server.json_rows(
        "SELECT JSON_OBJECT('projectName',`project_name`,'projectCompany',`project_unit`,"
        "'recordCode',`project_code`,'recordDate',`record_date`) FROM `filing_projects` "
        "WHERE `source` NOT LIKE 'Excel%' AND `record_date`<>''",
        config,
    )
    by_code, by_pair = build_date_indexes(official)
    sales = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'projectName',`company_name`,"
        "'projectCompany',`project_unit`,'recordCode',`credit_code`,'recordDate',`record_date`) "
        "FROM `sales_leads` WHERE `source` LIKE 'Excel%'",
        config,
    )
    filings = server.json_rows(
        "SELECT JSON_OBJECT('id',CAST(`id` AS CHAR),'projectName',`project_name`,"
        "'projectCompany',`project_unit`,'recordCode',`project_code`,'recordDate',`record_date`) "
        "FROM `filing_projects` WHERE `source` LIKE 'Excel%'",
        config,
    )

    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    sales_backup = f"sales_leads_backup_{suffix}_datefix"
    filing_backup = f"filing_projects_backup_{suffix}_datefix"
    server.run_mysql(
        f"CREATE TABLE {server.quote_identifier(sales_backup)} LIKE `sales_leads`;"
        f"INSERT INTO {server.quote_identifier(sales_backup)} SELECT * FROM `sales_leads`;"
        f"CREATE TABLE {server.quote_identifier(filing_backup)} LIKE `filing_projects`;"
        f"INSERT INTO {server.quote_identifier(filing_backup)} SELECT * FROM `filing_projects`;",
        config,
    )

    statements = []
    sales_resolved = 0
    filing_resolved = 0
    for row in sales:
        date_text = resolved_date(row, by_code, by_pair)
        sales_resolved += bool(date_text)
        statements.append(
            f"UPDATE `sales_leads` SET `record_date`={server.sql_literal(date_text)} "
            f"WHERE `id`={int(row['id'])} LIMIT 1;"
        )
    for row in filings:
        date_text = resolved_date(row, by_code, by_pair)
        filing_resolved += bool(date_text)
        statements.append(
            f"UPDATE `filing_projects` SET `record_date`={server.sql_literal(date_text)} "
            f"WHERE `id`={int(row['id'])} LIMIT 1;"
        )

    batch = []
    length = 0
    for statement in statements:
        if batch and length + len(statement) > 12000:
            server.run_mysql("START TRANSACTION;" + "".join(batch) + "COMMIT;", config)
            batch, length = [], 0
        batch.append(statement)
        length += len(statement)
    if batch:
        server.run_mysql("START TRANSACTION;" + "".join(batch) + "COMMIT;", config)

    print(json.dumps({
        "salesRows": len(sales), "salesResolved": sales_resolved, "salesUndated": len(sales) - sales_resolved,
        "filingRows": len(filings), "filingResolved": filing_resolved, "filingUndated": len(filings) - filing_resolved,
        "salesBackup": sales_backup, "filingBackup": filing_backup,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
