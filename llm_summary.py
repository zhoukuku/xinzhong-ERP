# -*- coding: utf-8 -*-
"""LLM 调度器 - 根据 config 选择 provider, 真正调用下放给具体模块.

provider:
    - doubao-web  豆包网页版 (免费, 需要 Chrome + 手动登录, 走 llm_doubao_web.py)
    - zhipu       智谱 GLM-4-Flash (完全免费 API, 走 llm_zhipu.py)
    - doubao-api  字节豆包 API (有免费额度, 走本文件内置)
    - deepseek    DeepSeek (便宜, 走本文件内置)
    - qwen        通义千问 (部分免费, 走本文件内置)

提供统一函数: summarize(row, cfg) -> dict (DB 字段映射结果)
"""
from __future__ import annotations

import os
import sys
import json
import time
import sqlite3
import argparse
import logging
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / "projects.db"
LOG_FILE = ROOT / "llm_summary.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("llm_summary")


# ===== 配置 =====
def load_config() -> dict:
    cfg_path = ROOT / "config.json"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ===== Prompt =====
SYSTEM_PROMPT = """你是新能源项目公开信息调查员，负责为光伏支架工厂筛选可电话跟进的项目线索。

边界：
1. 只使用可核验的公开网页信息；无法确认写[未确认]，未公开写[未公开]。
2. 不得把企业注册地址当作项目建设地址。
3. 法定代表人、执行董事/经理、股东、实际控制人、项目负责人必须分开表述，不得推定为同一人。
4. 手机号必须附公开来源；没有来源不得猜测。
5. 豆包负责项目地址、建设内容、进展和主体线索；工商股权、注册地址和电话最终由探迹复核。
6. 只返回一个合法 JSON 对象，不要 Markdown，不要解释性前后缀。"""


USER_PROMPT_TEMPLATE = """待调查项目：{name}
备案项目单位：{unit}

目标：识别项目真正的投资/运营主体和可联系决策人，为光伏支架采购业务提供可核验线索。备案项目单位可能是项目壳公司，不要直接认定为最终主体。

调查顺序：
1. 先核实项目实际建设地址、装机规模、建设内容、备案及施工/并网进展。
2. 再列出备案项目单位的一级股东、二级股东和可能的最终控股方；每层单独记录，不得跳层。
3. 区分法定代表人、执行董事/经理、股东自然人、实际控制人和项目负责人。
4. 搜索同一控股体系下新能源、光伏、储能、工程类关联企业。
5. 搜索历史光伏项目、EPC/支架采购、招投标、融资、扩建和合作建厂线索。
6. 给出建议在探迹核验的企业全称，只能给一个最优目标；证据不足时返回“未确认”，不得把备案项目单位冒充为最终主体。

补充已知线索 (从其他渠道抓到的, 可不重复查):
- 备案编号: {credit_code}
- 立项时间: {record_date}
- 联系人: {contact_person}
- 电话: {phone}
- 地址: {address}
- 主体公司: {main_company}
- 投资人/股东: {investor}
- 项目情况: {project_desc}
- 项目进展: {project_status}
- 备注: {remark}

严格按以下结构返回，所有字段必须存在：
{{
  "项目地址": "项目实际建设地址，不是企业注册地址",
  "建设规模": "装机容量/建设内容/总投资，未知写[未确认]",
  "项目情况": "一句话说明建设内容和当前状态",
  "项目进展": "已备案/设计/采购/EPC招标/施工/并网等已核实节点",
  "备案公司": "{unit}",
  "一级股东": [{{"名称":"", "持股比例":"", "类型":"企业/个人", "证据序号":[]}}],
  "背后控股公司": "直接或最相关的控股企业全称",
  "最终主体公司": "最可能实际出资或运营的企业全称",
  "建议探迹查询主体公司": "只填一个企业全称",
  "最终实际控制人": "姓名或机构；证据不足写[未确认]",
  "法定代表人": "",
  "执行董事或经理": "",
  "控股人姓名": "不得把法定代表人直接等同实际控制人",
  "控股人手机号": "仅公开且有证据的号码，否则[未公开]",
  "关键对接人": [{{"姓名":"", "职务":"", "电话":"", "电话证据序号":[]}}],
  "股权穿透": {{"层级":[{{"层级":"备案公司/一级/二级/最终", "主体":"", "持股比例":"", "关系":"", "证据序号":[]}}], "最终控股方":"", "实际控制人":"", "核验结论":""}},
  "备案主体类型": "项目壳公司/自有投资运营主体/无法判断",
  "备案逻辑分析": "结论和依据",
  "关联企业": [],
  "历史光伏项目": [],
  "历史招投标": [],
  "光伏EPC记录": [],
  "潜在采购机会": "支架/EPC配套/车棚结构等切入点",
  "潜在线索": [],
  "待核实字段": [],
  "信息源": [{{"序号":1, "标题":"", "链接":"完整URL", "发布日期":"", "支持结论":""}}]
}}

严禁输出示例、测试或“某某”名称。每个关键股权结论必须引用信息源序号；没有证据就写[未确认]。"""


def build_user_prompt(row: dict) -> str:
    return USER_PROMPT_TEMPLATE.format(
        name=row.get("company_name", ""),
        unit=row.get("project_unit", ""),
        credit_code=row.get("credit_code", ""),
        record_date=row.get("record_date", ""),
        contact_person=row.get("contact_person", "未公开"),
        phone=row.get("phone", "未公开"),
        address=row.get("address", "未公开"),
        main_company=row.get("main_company", "无 (可能为业主企业自投)"),
        investor=row.get("investor", "未公开"),
        project_desc=row.get("project_desc", "(无, 请通过联网搜索补充)"),
        project_status=row.get("project_status", "(无, 请通过联网搜索补充)"),
        remark=row.get("remark", "(无)"),
    )


# ===== 豆包 6 维度 -> DB 字段映射 =====
def _first_contact_name(contacts: list) -> str:
    for target_role in ("法人", "法定代表人", "总经理", "执行董事", "项目负责人"):
        for c in contacts:
            if target_role in (c.get("职务") or ""):
                return c.get("姓名", "")
    if contacts:
        return contacts[0].get("姓名", "")
    return ""


def _first_contact_phone(contacts: list) -> str:
    for c in contacts:
        phone = c.get("电话", "")
        if phone and phone not in ("[未公开]", "[未确认]", ""):
            return phone
    return ""


def call_mock(prompt: str, row: dict, cfg: dict) -> dict | None:
    """Mock LLM - 用于端到端测试, 不发真实请求."""
    try:
        from llm_mock import mock_response
        return mock_response(row)
    except Exception as e:
        log.error("Mock 调用异常: %s", str(e)[:120])
        return None


def dd_to_db(result: dict) -> dict:
    """豆包 6 维度 JSON -> DB 字段映射."""
    if not result:
        return {}

    parts = []
    parts.append(f"【公司性质】{result.get('公司性质', '')}")
    parts.append(f"【最终控股方】{result.get('股权穿透', {}).get('最终控股方', '')}")
    parts.append(f"【实控人】{result.get('股权穿透', {}).get('实际控制人', '')}")
    contacts = result.get("关键对接人", [])
    if contacts:
        contact_str = "; ".join(
            f"{c.get('姓名', '')}({c.get('职务', '')}) {c.get('电话', '')}"
            for c in contacts if c.get("姓名")
        )
        parts.append(f"【关键对接人】{contact_str}")
    if result.get("备案逻辑分析"):
        parts.append(f"【备案逻辑】{result['备案逻辑分析']}")
    if result.get("潜在线索"):
        parts.append(f"【潜在线索】" + "; ".join(result["潜在线索"][:3]))
    if result.get("销售建议"):
        parts.append(f"【销售建议】{result['销售建议']}")

    summary = "\n".join(parts)

    return {
        "remark": json.dumps(result, ensure_ascii=False, indent=2)[:8000],
        "project_desc": result.get("项目情况", ""),
        "project_status": result.get("项目进展", ""),
        "location": result.get("项目所在地", ""),
        "contact_person": _first_contact_name(contacts),
        "phone": _first_contact_phone(contacts),
        "summary": summary,
    }


# ===== 各 provider 调用入口 =====
def call_doubao_web(prompt: str) -> dict | None:
    """豆包网页版 - 直接 import llm_doubao_web 模块."""
    try:
        from llm_doubao_web import call_doubao
        return call_doubao(prompt, system=SYSTEM_PROMPT)
    except Exception as e:
        log.error("豆包网页调用异常: %s", str(e)[:120])
        return None


# call_zhipu 已移除 (不用 API)


# call_api 已移除 (只用豆包网页版)


def summarize(row: dict, cfg: dict | None = None) -> dict | None:
    """统一入口: 给一行 DB row, 返回 dd_to_db 后的 dict.

    返回 None 表示调用失败.
    """
    cfg = cfg or load_config()
    provider = cfg.get("llm", {}).get("provider", "doubao-web")
    prompt = build_user_prompt(row)

    log.info("provider: %s", provider)

    if provider == "doubao-web":
        result = call_doubao_web(prompt)
    elif provider == "mock":
        result = call_mock(prompt, row, cfg)
    else:
        log.error("未知 provider: %s (仅支持 doubao-web / mock)", provider)
        return None

    return dd_to_db(result) if result else None


# ===== DB =====
def fetch_pending(conn: sqlite3.Connection, limit: int) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM companies
        WHERE (summary = '' OR summary IS NULL) AND project_unit != ''
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cur.fetchall()]


def update_summary(conn: sqlite3.Connection, name: str, db_data: dict) -> None:
    cur = conn.cursor()
    cur.execute("""
        UPDATE companies SET
            contact_person = COALESCE(NULLIF(?, ''), contact_person),
            phone = COALESCE(NULLIF(?, ''), phone),
            project_desc = COALESCE(NULLIF(?, ''), project_desc),
            project_status = COALESCE(NULLIF(?, ''), project_status),
            location = COALESCE(NULLIF(?, ''), location),
            remark = COALESCE(NULLIF(?, ''), remark),
            summary = COALESCE(NULLIF(?, ''), summary)
        WHERE company_name = ?
    """, (
        db_data.get("contact_person", ""), db_data.get("phone", ""),
        db_data.get("project_desc", ""), db_data.get("project_status", ""),
        db_data.get("location", ""), db_data.get("remark", ""),
        db_data.get("summary", ""), name,
    ))


# ===== 主流程 (调度器本身也能跑) =====
def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 调度器")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--company", help="单条")
    parser.add_argument("--provider", help="临时切换 provider")
    parser.add_argument("--dry-run", action="store_true", help="看 prompt")
    args = parser.parse_args()

    cfg = load_config()
    if args.provider:
        cfg.setdefault("llm", {})["provider"] = args.provider
    provider = cfg.get("llm", {}).get("provider", "doubao-web")
    log.info("provider: %s", provider)

    if not DB_PATH.exists():
        log.error("DB 不存在")
        return 1
    conn = sqlite3.connect(str(DB_PATH))
    if args.company:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE company_name LIKE ?",
                    (f"%{args.company}%",))
        targets = [dict(r) for r in cur.fetchall()]
    else:
        targets = fetch_pending(conn, args.limit)
    log.info("待处理: %d 条", len(targets))

    if args.dry_run:
        for row in targets[:1]:
            print(build_user_prompt(row)[:500])
        return 0

    updated = 0
    for i, row in enumerate(targets, 1):
        name = row["company_name"]
        log.info("[%d/%d] %s", i, len(targets), name[:30])
        db_data = summarize(row, cfg)
        if db_data:
            update_summary(conn, name, db_data)
            updated += 1
            log.info("  >> summary: %s", (db_data.get("summary") or "")[:80].replace("\n", " "))
        else:
            log.warning("  -- 跳过")
        time.sleep(2)

    conn.commit()
    conn.close()
    log.info("=" * 50)
    log.info("本次更新: %d / %d 条", updated, len(targets))
    log.info("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
