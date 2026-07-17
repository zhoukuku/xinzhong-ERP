# -*- coding: utf-8 -*-
"""豆包网页版 LLM 自动化 (完全免费, 无需 API).

架构:
    Chrome --remote-debugging-port=9223 --user-data-dir=browser_debug_profile_doubao
    用户首次手动登录 -> 登录态持久化 -> 脚本 attach 复用

使用:
    # 1. 启动 Chrome (一次性)
    powershell -File start_chrome_doubao.ps1

    # 2. 在弹出的 Chrome 中手动登录豆包

    # 3. 测试 (不进 DB)
    python llm_doubao_web.py --prompt "你好" --dry-run       # 只看 prompt
    python llm_doubao_web.py --prompt "你好"                 # 真发一条
    python llm_doubao_web.py --test-input                    # 填入并截图, 不发送

    # 4. 跑数据
    python llm_doubao_web.py --company "XX项目"
    python llm_doubao_web.py --limit 10 --source caitoubiao
    python llm_doubao_web.py                                # 默认: 所有 summary 为空的

加固项:
    - 多重 selector fallback (实测 + 备选)
    - 登录过期自动检测 + 重新提示登录
    - JSON 提取: 兼容 ```json``` 包裹, 纯文本, 部分 JSON
    - 等待回复: 检测"停止生成"按钮, 自动判断完成
    - 重试机制: 网络错误/超时自动重试
    - --test-input 模式: 把 prompt 填进输入框 + 截图, 让你目视确认
"""
from __future__ import annotations

import os
import sys
import json
import time
import sqlite3
import argparse
import logging
import re
import subprocess
import urllib.request
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / "projects.db"
LOG_FILE = ROOT / "llm_doubao_web.log"

DOUBAO_URL = "https://www.doubao.com/chat/"
DOUBAO_DEBUG_PORT = 9223
DOUBAO_PROFILE = ROOT / "browser_debug_profile_doubao"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("doubao_web")


# ===== Chrome 启动 / 附加 =====
def chrome_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def launch_chrome(port: int, profile_dir: Path) -> None:
    profile_dir.mkdir(exist_ok=True)
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--new-window",
        "about:blank",
    ]
    log.info("启动 Chrome: port=%d profile=%s", port, profile_dir.name)
    subprocess.Popen(cmd, shell=False,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)


def attach_driver(port: int, profile_dir: Path):
    """attach 到现有 Chrome. 失败抛错."""
    from selenium import webdriver
    from selenium.webdriver import ChromeOptions
    if not chrome_running(port):
        launch_chrome(port, profile_dir)
        time.sleep(2)
    opts = ChromeOptions()
    opts.binary_location = CHROME_PATH
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    try:
        driver = webdriver.Chrome(options=opts)
        log.info("已附加 Chrome: %s", driver.current_url[:80])
        return driver
    except Exception as e:
        log.error("附加 Chrome 失败: %s", str(e)[:150])
        log.error("请确认: start_chrome_doubao.ps1 已运行, 端口 %d 可达", port)
        raise


# ===== 登录态检测 =====
LOGIN_MARKERS = ["立即登录", "登录后体验", "扫码登录", "未登录", "请先登录", "登录解锁"]


def is_doubao_logged_in(driver) -> bool:
    """检测豆包是否已登录.

    判定: body 不包含强登录提示, 且顶部没有"登录"按钮.
    """
    try:
        body = driver.execute_script("return document.body.innerText") or ""
        for marker in LOGIN_MARKERS:
            if marker in body:
                return False
        # 顶部按钮里没有"登录"文字
        from selenium.webdriver.common.by import By
        for el in driver.find_elements(By.TAG_NAME, "button"):
            try:
                if el.is_displayed() and "登录" in (el.text or "").strip():
                    return False
            except Exception:
                pass
        return True
    except Exception:
        return False


def wait_manual_login(driver, timeout_sec: int = 300) -> bool:
    """阻塞等待手动登录. 每 5 秒检测一次."""
    log.info("=" * 60)
    log.info("需要手动登录豆包!")
    log.info("请在弹出的 Chrome 中完成扫码/手机号登录")
    log.info("登录成功后此脚本会自动继续...")
    log.info("=" * 60)
    if "doubao.com" not in driver.current_url:
        driver.get(DOUBAO_URL)
    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(5)
        if is_doubao_logged_in(driver):
            log.info("检测到登录成功! 继续...")
            return True
    log.error("手动登录超时 (%ds)", timeout_sec)
    return False


# ===== DOM 选择器 =====
# 实测确认: 豆包 chat 页输入框就是 textarea[placeholder*='发消息']
INPUT_SELECTORS = [
    "textarea[placeholder*='发消息']",
    "textarea.semi-input-textarea",
    "textarea[placeholder*='请输入']",
    "textarea",
    "div[contenteditable='true']",
]

# 发送按钮: 豆包是带 svg 图标的 button (没有特定 aria-label)
SEND_BUTTON_XPATHS = [
    "//button[.//svg and not(@disabled)]",
    "//button[@type='button' and not(@disabled)]",
]

# "停止生成" 按钮 - 用于判断回复是否完成
STOP_MARKERS = ["停止生成", "停止回答", "Stop generating", "停止", "重新生成"]


def find_input(driver, timeout: int = 10):
    """找输入框. 返回 element 或 None."""
    from selenium.webdriver.common.by import By
    end = time.time() + timeout
    while time.time() < end:
        for sel in INPUT_SELECTORS:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception:
                pass
        time.sleep(0.5)
    return None


def find_send_button(driver):
    """找发送按钮."""
    from selenium.webdriver.common.by import By
    # Current Doubao chat uses a stable semantic class fragment for the
    # circular send control; prefer it over generic visible buttons.
    try:
        for btn in driver.find_elements(By.XPATH, "//button[contains(@class,'g-send-msg-btn-bg')]"):
            if btn.is_displayed() and btn.is_enabled():
                return btn
    except Exception:
        pass
    # 优先找输入框旁边的 button (相邻定位)
    try:
        inp = find_input(driver, timeout=2)
        if inp:
            # 在 input 父级容器内找 button
            try:
                parent = inp.find_element(By.XPATH, "..")
                for _ in range(3):
                    buttons = parent.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            # 排除纯图标按钮(可能不是发送)
                            return btn
                    parent = parent.find_element(By.XPATH, "..")
            except Exception:
                pass
    except Exception:
        pass
    # 兜底: 找任意可见未禁用的 button
    for xpath in SEND_BUTTON_XPATHS:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    return btn
        except Exception:
            pass
    return None


def is_generating(driver) -> bool:
    """检测豆包是否还在生成中."""
    try:
        body = driver.execute_script("return document.body.innerText") or ""
        for marker in STOP_MARKERS:
            if marker in body:
                return True
    except Exception:
        pass
    return False


def wait_reply_done(driver, timeout_sec: int = 240, poll_interval: float = 2.0, baseline: str = "") -> bool:
    """等待回复完成.

    策略: 检测"停止生成"按钮出现 -> 等它消失 -> 再缓冲 2s 让 DOM 完全渲染.
    """
    from selenium.webdriver.common.by import By
    start = time.time()
    generating_seen = False
    baseline = baseline or (driver.execute_script("return document.body.innerText") or "")
    log.info("  等回复 (最长 %ds)...", timeout_sec)
    while time.time() - start < timeout_sec:
        try:
            gen = is_generating(driver)
        except Exception:
            gen = False
        if gen:
            generating_seen = True
            time.sleep(poll_interval)
            continue
        if generating_seen:
            time.sleep(2)
            log.info("  回复完成 (耗时 %ds)", int(time.time() - start))
            return True
        # Current chat messages use a left-aligned streaming container for
        # assistant replies. This avoids mistaking the user's newly sent
        # prompt for a reply when no stop button is rendered.
        try:
            assistant_blocks = driver.find_elements(By.CSS_SELECTOR, "div.flex.justify-start div[data-streaming]")
            if any(e.is_displayed() and len((e.text or '').strip()) > 20 for e in assistant_blocks):
                time.sleep(2)
                if not is_generating(driver):
                    log.info("  回复完成 (assistant 容器, 耗时 %ds)", int(time.time() - start))
                    return True
        except Exception:
            pass
        # Anonymous chat may finish without exposing a "停止生成" marker.
        # A changed body with a substantial new answer is sufficient then.
        try:
            current = driver.execute_script("return document.body.innerText") or ""
            if len(current) > len(baseline) + 80:
                time.sleep(2)
                if not is_generating(driver):
                    log.info("  回复完成 (无生成标记, 耗时 %ds)", int(time.time() - start))
                    return True
        except Exception:
            pass
        time.sleep(poll_interval)
    log.warning("  回复等待超时 (%ds), generating_seen=%s", timeout_sec, generating_seen)
    return generating_seen   # 即使超时, 也尝试取已生成的内容


def get_last_reply(driver) -> str:
    """取最后一条 AI 回复的纯文本."""
    from selenium.webdriver.common.by import By
    try:
        assistant = driver.find_elements(By.CSS_SELECTOR, "div.flex.justify-start div[data-streaming]")
        for el in reversed(assistant):
            text = (el.text or "").strip()
            if len(text) > 20:
                return text
    except Exception:
        pass
    # 策略 1: 找 markdown 容器
    for sel in [
        "div[class*='markdown']",
        "div[class*='message-content']",
        "div[class*='answer']",
        "div[data-message-role='assistant']",
        "div[class*='assistant']",
    ]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                # 取最后一个且非空
                for el in reversed(els):
                    txt = (el.text or "").strip()
                    if len(txt) > 30:   # 过滤短文本
                        return txt
        except Exception:
            pass
    # 策略 2: 兜底取 body 末尾
    try:
        body = driver.execute_script("return document.body.innerText") or ""
        return body[-5000:]
    except Exception:
        return ""


# ===== JSON 提取 (鲁棒) =====
def extract_json(text: str) -> dict | None:
    """从豆包回复中提取 JSON. 多策略.

    1. ```json ... ``` 包裹
    2. 第一个 { 到匹配 }
    3. 尝试修复常见错误 (单引号, 末尾逗号)
    """
    if not text:
        return None
    # 策略 1: markdown 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 策略 2: 找最大 { ... } 块
    candidates = []
    for m in re.finditer(r"\{", text):
        depth = 0
        start = m.start()
        for i in range(start, min(len(text), start + 50000)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    # 优先最长的(可能更完整)
    for cand in sorted(candidates, key=len, reverse=True)[:3]:
        try:
            return json.loads(cand)
        except Exception:
            # 尝试修复常见错误
            fixed = cand.replace("\u201c", '"').replace("\u201d", '"')
            fixed = re.sub(r",\s*}", "}", fixed)
            fixed = re.sub(r",\s*]", "]", fixed)
            try:
                return json.loads(fixed)
            except Exception:
                continue
    return None


# ===== 核心: 发送 prompt 拿回复 =====
def send_prompt(driver, prompt: str, timeout_sec: int = 240) -> str | None:
    """发一条 prompt, 等回复, 返回文本. 失败 None."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    # 1. 跳到 chat 页
    # Each investigation starts a clean conversation. Reusing a previous
    # chat can leave the next task waiting behind an unfinished response.
    log.info("  打开豆包新对话...")
    driver.get(DOUBAO_URL)
    time.sleep(3)

    # 2. 找输入框
    inp = find_input(driver, timeout=10)
    if not inp:
        log.error("  找不到输入框 (selector 全部失败, 豆包可能改版)")
        return None

    # Capture the conversation before sending. Anonymous or newer Doubao
    # pages may not expose a visible "停止生成" marker.
    baseline_body = driver.execute_script("return document.body.innerText") or ""

    # 3. 清空 + 填入
    try:
        inp.click()
        time.sleep(0.3)
        # Doubao's current Semi textarea ignores WebDriver key events. The
        # browser editing command updates both the DOM value and React state.
        driver.execute_script("arguments[0].focus(); document.execCommand('selectAll', false, null); document.execCommand('insertText', false, arguments[1]);", inp, prompt)
        if (inp.get_attribute("value") or "") != prompt:
            driver.execute_script(
                "var el=arguments[0];"
                "var setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;"
                "setter.call(el, arguments[1]);"
                "el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:arguments[1]}));",
                inp, prompt,
            )
        time.sleep(0.5)
    except Exception as e:
        log.error("  填入 prompt 失败: %s", str(e)[:100])
        return None

    # 4. 点发送 (优先按钮, 否则 Ctrl+Enter)
    btn = find_send_button(driver)
    if btn:
        try:
            btn.click()
            log.info("  已点击发送")
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", btn)
                log.info("  JS 点击发送")
            except Exception:
                inp.send_keys(Keys.RETURN)
                log.info("  回车发送")
    else:
        inp.send_keys(Keys.RETURN)
        log.info("  找不到发送按钮, 回车发送")

    # 5. 等回复
    if not wait_reply_done(driver, timeout_sec=timeout_sec, baseline=baseline_body):
        return None

    return get_last_reply(driver)


# ===== 登录过期自动重试 =====
def ensure_session(driver, timeout_sec: int = 300) -> bool:
    """确保登录态. 过期则引导重新登录."""
    if is_doubao_logged_in(driver):
        return True
    log.warning("检测到豆包未登录或登录过期, 需要重新登录")
    return wait_manual_login(driver, timeout_sec=timeout_sec)


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


# ===== 主流程 =====
def call_doubao(driver, prompt: str, max_retry: int = 2) -> dict | None:
    """调豆包一次, 返回 JSON dict (失败 None). 失败自动重试."""
    for attempt in range(1, max_retry + 1):
        try:
            log.info("  [尝试 %d/%d] 发 prompt...", attempt, max_retry)
            reply = send_prompt(driver, prompt, timeout_sec=240)
            if not reply:
                log.warning("  无回复")
                continue
            log.info("  回复长度: %d", len(reply))
            result = extract_json(reply)
            if result:
                return result
            log.warning("  JSON 提取失败, 原回复前 200 字符: %s", reply[:200].replace(chr(10), " "))
        except Exception as e:
            log.error("  调用异常: %s", str(e)[:120])
            traceback.print_exc()
        time.sleep(3)
    return None


def test_input_mode(driver, prompt: str) -> None:
    """填入 prompt 到输入框, 截图, 不发送. 让你目视确认."""
    if "doubao.com" not in driver.current_url:
        driver.get(DOUBAO_URL)
        time.sleep(3)
    inp = find_input(driver, timeout=10)
    if not inp:
        log.error("找不到输入框")
        return
    inp.click()
    time.sleep(0.3)
    driver.execute_script(
        "var el=arguments[0];"
        "var setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;"
        "setter.call(el, arguments[1]);"
        "el.dispatchEvent(new Event('input',{bubbles:true}));",
        inp, prompt,
    )
    time.sleep(1)
    log.info("已填入 prompt (%d 字符), 截图...", len(prompt))
    ss_path = ROOT / f"test_input_{int(time.time())}.png"
    driver.save_screenshot(str(ss_path))
    log.info("截图保存: %s", ss_path)
    log.info("打开截图, 确认输入框里有内容. 然后手动点发送, 验证豆包回复.")


def main() -> int:
    parser = argparse.ArgumentParser(description="豆包网页版 LLM (免费, 无 API)")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--source", help="只处理某 source")
    parser.add_argument("--company", help="单条")
    parser.add_argument("--prompt", help="单条 prompt 测试")
    parser.add_argument("--dry-run", action="store_true", help="只打印 prompt")
    parser.add_argument("--test-input", action="store_true",
                        help="填入输入框 + 截图, 不发送")
    args = parser.parse_args()

    # 单条 prompt 测试
    if args.prompt:
        if args.dry_run:
            print(args.prompt)
            return 0
        driver = attach_driver(DOUBAO_DEBUG_PORT, DOUBAO_PROFILE)
        if not ensure_session(driver):
            return 1
        if args.test_input:
            test_input_mode(driver, args.prompt)
            return 0
        from llm_summary import build_user_prompt
        full_prompt = f"[角色] 你是新能源项目尽职调查分析师. 输出严格 JSON.\n\n{args.prompt}"
        result = call_doubao(driver, full_prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2) if result else "(无)")
        driver.quit()
        return 0

    if not DB_PATH.exists():
        log.error("DB 不存在")
        return 1

    # 准备 driver
    driver = attach_driver(DOUBAO_DEBUG_PORT, DOUBAO_PROFILE)
    if not ensure_session(driver):
        return 1

    # 准备 DB 目标
    conn = sqlite3.connect(str(DB_PATH))
    if args.company:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE company_name LIKE ?",
                    (f"%{args.company}%",))
        targets = [dict(r) for r in cur.fetchall()]
    else:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if args.source:
            cur.execute("""
                SELECT * FROM companies
                WHERE source=? AND (summary='' OR summary IS NULL) AND project_unit != ''
                ORDER BY id DESC LIMIT ?
            """, (args.source, args.limit))
        else:
            cur.execute("""
                SELECT * FROM companies
                WHERE (summary='' OR summary IS NULL) AND project_unit != ''
                ORDER BY id DESC LIMIT ?
            """, (args.limit,))
        targets = [dict(r) for r in cur.fetchall()]
    log.info("待处理: %d 条", len(targets))

    if args.dry_run:
        from llm_summary import build_user_prompt
        for row in targets[:1]:
            print(build_user_prompt(row)[:500])
        return 0

    from llm_summary import SYSTEM_PROMPT, build_user_prompt, dd_to_db

    updated = 0
    failed = 0
    for i, row in enumerate(targets, 1):
        name = row["company_name"]
        log.info("[%d/%d] %s", i, len(targets), name[:30])
        prompt = build_user_prompt(row)
        full = f"[系统设定] {SYSTEM_PROMPT}\n\n{prompt}"

        # 每 N 条检查一次登录态 (避免豆包中途登出)
        if i % 5 == 1 and not ensure_session(driver):
            log.error("登录态丢失, 中断")
            break

        result = call_doubao(driver, full, max_retry=2)
        if not result:
            failed += 1
            log.warning("  -- 失败 (累计 %d/%d)", failed, i)
            continue
        db_data = dd_to_db(result)
        update_summary(conn, name, db_data)
        updated += 1
        log.info("  >> OK: %s", (db_data.get("summary") or "")[:80].replace(chr(10), " "))
        time.sleep(2)

    conn.commit()
    conn.close()
    log.info("=" * 50)
    log.info("成功: %d / 失败: %d / 总: %d", updated, failed, len(targets))
    log.info("=" * 50)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
