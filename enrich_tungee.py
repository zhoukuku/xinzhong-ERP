# -*- coding: utf-8 -*-
"""探迹补全 - 完全脱离 main.py, 独立运行.

关键设计:
    - 复用 browser_debug_profile (port 9222) + 手动登录一次后永久复用
    - 不依赖 main.py 的类, 不引用 main.py 的 import
    - 从 config.json 读账号密码, 不硬编码
    - 输出 DB schema 与 import_caitoubiao 一致

启动:
    powershell -File start_chrome.ps1        # 启动 Chrome 9222
    # 浏览器中手动登录探迹 (一次)
    python enrich_tungee.py --limit 5        # 跑 5 条测试
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
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / "projects.db"
CONFIG_PATH = ROOT / "config.json"
LOG_FILE = ROOT / "enrich_tungee.log"

DEBUG_PORT = 9222
PROFILE_DIR = ROOT / "browser_debug_profile"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

TUNGEE_HOME = "https://user.tungee.com/home"
TUNGEE_SIGN_IN = "https://user.tungee.com/users/sign-in"
TUNGEE_SEARCH = "https://bidding.tungee.com/search-enterprise/home"
TUNGEE_UNLOCK_LIST = "https://bidding.tungee.com/unlock-list/enterprise"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("tungee")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


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
    from selenium import webdriver
    from selenium.webdriver import ChromeOptions
    if not chrome_running(port):
        launch_chrome(port, profile_dir)
    opts = ChromeOptions()
    opts.binary_location = CHROME_PATH
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    return webdriver.Chrome(options=opts)


def is_logged_in(driver) -> bool:
    driver.get(TUNGEE_HOME)
    time.sleep(3)
    body = driver.execute_script("return document.body.innerText") or ""
    return "拓客 · 招投标版" in body or "退出" in body or "退出账户" in body


def restore_session_cookies(driver, session_path: Path) -> bool:
    if not session_path.exists():
        return False
    try:
        cookies = json.loads(session_path.read_text(encoding="utf-8"))
        driver.get("https://user.tungee.com/")
        for cookie in cookies:
            payload = {
                key: value
                for key, value in cookie.items()
                if key in {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
                and value is not None
            }
            try:
                driver.add_cookie(payload)
            except Exception:
                continue
        return is_logged_in(driver)
    except Exception as exc:
        log.warning("恢复探迹登录会话失败: %s", exc)
        return False


def save_session_cookies(driver, session_path: Path) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(driver.get_cookies(), ensure_ascii=False), encoding="utf-8")


def enter_bidding_product(driver, timeout_sec: int = 20) -> bool:
    """Select the current enterprise's bidding product before opening search."""
    from selenium.webdriver.common.by import By

    if "bidding.tungee.com" in driver.current_url:
        body = driver.execute_script("return document.body.innerText") or ""
        if "请先选择登录企业" not in body and "登录信息失效" not in body:
            return True

    driver.get(TUNGEE_HOME)
    time.sleep(3)
    original_handles = set(driver.window_handles)
    product_link = None
    for element in driver.find_elements(By.CSS_SELECTOR, "a[role='button']"):
        text = element.text.replace("\n", " ").strip()
        if element.is_displayed() and "拓客" in text and "招投标版" in text:
            product_link = element
            break
    if not product_link:
        driver.get(TUNGEE_SEARCH)
        time.sleep(2)
        body = driver.execute_script("return document.body.innerText") or ""
        return "bidding.tungee.com" in driver.current_url and "登录信息失效" not in body

    driver.execute_script("arguments[0].click()", product_link)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(1)
        handles = driver.window_handles
        candidates = list(set(handles) - original_handles) + handles
        for handle in candidates:
            try:
                driver.switch_to.window(handle)
                if "bidding.tungee.com" in driver.current_url:
                    body = driver.execute_script("return document.body.innerText") or ""
                    return "请先选择登录企业" not in body and "登录信息失效" not in body
            except Exception:
                continue
    return False


def enter_enterprise_query(driver, timeout_sec: int = 20) -> bool:
    """Open 企业查询; the unlock list is never a valid search surface."""
    from selenium.webdriver.common.by import By

    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            if driver.current_url.startswith(TUNGEE_SEARCH):
                break
        except Exception:
            continue

    # Always correct product landing pages such as /unlock-list/enterprise.
    if not driver.current_url.startswith(TUNGEE_SEARCH):
        driver.get(TUNGEE_SEARCH)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(1)
        body = driver.execute_script("return document.body.innerText") or ""
        inputs = [item for item in driver.find_elements(By.CSS_SELECTOR, "input") if item.is_displayed()]
        if driver.current_url.startswith(TUNGEE_SEARCH) and inputs:
            for candidate in inputs:
                placeholder = candidate.get_attribute("placeholder") or ""
                if "企业名" in placeholder or "人名" in placeholder or "品牌名" in placeholder:
                    return True
    return False


def is_unlock_action_text(value: str) -> bool:
    compact = re.sub(r"\s+", "", str(value or ""))
    return compact == "解锁" or any(
        marker in compact
        for marker in ("立即解锁", "解锁企业并查看", "解锁以查看全部", "查看号码", "查看联系方式")
    )


def unlock_company(driver, timeout_sec: int = 15) -> bool:
    """Click the detail-page unlock action when contact data is protected."""
    from selenium.webdriver.common.by import By

    candidates = driver.find_elements(By.XPATH, "//*[self::button or @role='button' or self::a]")
    clicked = False
    for element in candidates:
        href = element.get_attribute("href") or ""
        if element.is_displayed() and "/unlock-list/" not in href and is_unlock_action_text(element.text):
            driver.execute_script("arguments[0].click()", element)
            clicked = True
            break
    if not clicked:
        return True

    time.sleep(1)
    for element in driver.find_elements(By.XPATH, "//*[self::button or @role='button']"):
        compact = re.sub(r"\s+", "", element.text or "")
        if element.is_displayed() and compact in {"确定", "确认", "确认解锁", "立即解锁"}:
            driver.execute_script("arguments[0].click()", element)
            break
    time.sleep(2)
    body = driver.execute_script("return document.body.innerText") or ""
    return "余额不足" not in body and "解锁失败" not in body


def select_account_login(driver) -> bool:
    """Switch the sign-in page from QR login to account/password login."""
    from selenium.webdriver.common.by import By

    for element in driver.find_elements(By.CSS_SELECTOR, "div._2me12[role='button']"):
        if element.is_displayed() and element.text.strip() == "账号登录":
            driver.execute_script("arguments[0].click()", element)
            return True
    return False


def wait_manual_login(driver, timeout_sec: int = 300) -> bool:
    log.info("=" * 60)
    log.info("需要手动登录探迹! 请在 Chrome 中完成登录")
    log.info("登录成功后此窗口会自动继续...")
    log.info("=" * 60)
    driver.get(TUNGEE_SIGN_IN)
    time.sleep(1)
    select_account_login(driver)
    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(5)
        if is_logged_in(driver):
            log.info("登录成功!")
            return True
    return False


def normalize_company_name_for_match(value: str) -> str:
    """Build a stable comparison key for Chinese legal company names."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s\u200b\ufeff]+", "", text).casefold()


LEGAL_NAME_SUFFIXES = (
    "有限责任公司", "股份有限公司", "集团有限公司", "实业有限公司",
    "新能源科技有限公司", "科技有限公司", "有限公司", "集团公司",
    "合伙企业(有限合伙)", "合伙企业", "公司", "企业",
)


def company_name_stem(value: str) -> str:
    text = normalize_company_name_for_match(value)
    for suffix in LEGAL_NAME_SUFFIXES:
        normalized_suffix = normalize_company_name_for_match(suffix)
        if text.endswith(normalized_suffix) and len(text) > len(normalized_suffix):
            return text[:-len(normalized_suffix)]
    return text


def company_geo_prefix(value: str) -> str:
    stem = company_name_stem(value)
    for municipality in ("北京", "上海", "天津", "重庆", "香港", "澳门"):
        if stem.startswith(municipality):
            return municipality
    match = re.match(r"^([\u4e00-\u9fff]{1,6}?(?:省|市|县|区|自治州|自治区))", stem)
    return match.group(1) if match else ""


def company_name_match_score(target: str, candidate: str, rank: int = 0) -> float:
    """Score a Tungee candidate without accepting a same-brand company in another city."""
    target_key = normalize_company_name_for_match(target)
    candidate_key = normalize_company_name_for_match(candidate)
    if not target_key or not candidate_key:
        return 0.0
    if target_key == candidate_key:
        return 1.0

    target_stem = company_name_stem(target)
    candidate_stem = company_name_stem(candidate)
    target_geo = company_geo_prefix(target)
    candidate_geo = company_geo_prefix(candidate)
    if target_geo and candidate_geo and target_geo != candidate_geo:
        return 0.0

    sequence = SequenceMatcher(None, target_stem, candidate_stem).ratio()
    prefix_size = len(os.path.commonprefix([target_stem, candidate_stem]))
    prefix_ratio = prefix_size / max(1, min(len(target_stem), len(candidate_stem)))
    target_brand = target_stem[len(target_geo):] if target_geo and target_stem.startswith(target_geo) else target_stem
    candidate_brand = candidate_stem[len(candidate_geo):] if candidate_geo and candidate_stem.startswith(candidate_geo) else candidate_stem
    longest = SequenceMatcher(None, target_brand, candidate_brand).find_longest_match()
    brand_overlap = longest.size / max(1, min(len(target_brand), len(candidate_brand)))
    geo_bonus = 0.20 if target_geo and target_geo == candidate_geo else 0.0
    containment_bonus = 0.08 if target_stem in candidate_stem or candidate_stem in target_stem else 0.0
    rank_bonus = max(0.0, 0.05 - max(0, rank) * 0.005)
    return min(1.0, sequence * 0.50 + prefix_ratio * 0.20 + brand_overlap * 0.17 + geo_bonus + containment_bonus + rank_bonus)


def company_search_candidates(value: str) -> list[str]:
    """Try full legal names first, then safe shorter terms for Tungee recall."""
    original = re.sub(r"[\u200b\ufeff]", "", str(value or "")).strip()
    ascii_parentheses = original.replace("（", "(").replace("）", ")")
    chinese_parentheses = ascii_parentheses.replace("(", "（").replace(")", "）")
    stem = company_name_stem(original)
    geo = company_geo_prefix(original)
    brand = stem[len(geo):] if geo and stem.startswith(geo) else stem
    candidates = []
    for candidate in (original, chinese_parentheses, ascii_parentheses, stem, f"{geo}{brand}" if geo else "", brand):
        candidate = re.sub(r"\s+", "", candidate)
        if len(candidate) >= 2 and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def is_recoverable_browser_error(error: Exception | str) -> bool:
    text = str(error).lower()
    return any(
        marker in text
        for marker in (
            "stale element",
            "timed out",
            "timeout",
            "connection aborted",
            "connectionreseterror",
            "httpconnectionpool",
            "disconnected",
            "target frame detached",
        )
    )


def search_company(driver, name: str, timeout: int = 30) -> str | None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    # The bidding homepage also has a visible input, but it searches tender
    # titles rather than enterprises. Always switch to 企业查询 first.
    if not enter_enterprise_query(driver, timeout_sec=timeout):
        log.warning("探迹未进入企业查询页面")
        return None
    target_key = normalize_company_name_for_match(name)
    deadline = time.time() + max(timeout * 2, 60)
    last_error = None
    best_match = None
    for query_name in company_search_candidates(name):
        if time.time() >= deadline:
            break
        try:
            inp = WebDriverWait(driver, min(20, max(2, int(deadline - time.time())))).until(
                lambda current: next(
                    (
                        candidate
                        for candidate in current.find_elements(By.CSS_SELECTOR, "input")
                        if candidate.is_displayed()
                        and any(
                            marker in (candidate.get_attribute("placeholder") or "")
                            for marker in ("企业名", "人名", "品牌名")
                        )
                    ),
                    None,
                )
            )
            driver.execute_script(
                """
                const input = arguments[0];
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(input, arguments[1]);
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                inp,
                query_name,
            )
            buttons = [
                button
                for button in driver.find_elements(By.XPATH, "//button[contains(normalize-space(.),'查询一下')]")
                if button.is_displayed()
            ]
            if buttons:
                driver.execute_script("arguments[0].click()", buttons[0])
            else:
                inp.send_keys(Keys.RETURN)
            time.sleep(2)

            query_deadline = min(deadline, time.time() + 6)
            while time.time() < query_deadline:
                links = driver.execute_script(
                    """
                    return Array.from(document.querySelectorAll("a[href*='/enterprise-details/'],a[href*='enterprise']"))
                      .slice(0, 50).map(item => ({href: item.href || '', text: item.innerText || ''}));
                    """
                ) or []
                for rank, link in enumerate(links):
                    candidate_name = (link.get("text") or "").strip()
                    link_key = normalize_company_name_for_match(candidate_name)
                    href = link.get("href") or ""
                    normalized_href = href if href.startswith("http") else "https://bidding.tungee.com" + href
                    if target_key and target_key == link_key:
                        return normalized_href
                    score = company_name_match_score(name, candidate_name, rank)
                    if not best_match or score > best_match[0]:
                        best_match = (score, normalized_href, candidate_name, query_name)
                if best_match and best_match[0] >= 0.78:
                    log.info(
                        "  企业模糊命中: %s -> %s (%.2f, query=%s)",
                        name, best_match[2], best_match[0], best_match[3],
                    )
                    return best_match[1]
                time.sleep(0.5)
        except Exception as exc:
            last_error = exc
            if is_recoverable_browser_error(exc):
                raise
            log.warning("  企业查询候选 %s 失败: %s", query_name, str(exc)[:120])
    if last_error and is_recoverable_browser_error(last_error):
        raise last_error
    # Never unlock or store a low-confidence first result.
    return None


def parse_shareholders(text: str) -> list[dict]:
    """Parse the shareholder table shown on a Tungee enterprise detail page."""
    parts = re.split(r"股东信息\d*", text)
    sections = [
        re.split(r"主要人员\d*|对外投资\d*|工商变更\d*", part, maxsplit=1)[0]
        for part in parts[1:]
    ]
    section = next((item for item in sections if "%" in item), "")
    if not section:
        return []
    pattern = re.compile(
        r"([\u4e00-\u9fffA-Za-z0-9（）()·]{4,100}?(?:有限责任公司|股份有限公司|有限公司|集团公司|合伙企业（有限合伙）|合伙企业\(有限合伙\)|合伙企业))"
        r"(?P<tail>.{0,120}?)(?P<ratio>\d+(?:\.\d+)?)\s*%",
        re.DOTALL,
    )
    shareholders = []
    seen = set()
    for match in pattern.finditer(section):
        name = match.group(1).strip()
        if name in seen:
            continue
        seen.add(name)
        tail = match.group("tail")
        shareholders.append(
            {
                "name": name,
                "ratio": float(match.group("ratio")),
                "type": "company",
                "controlling": "控股股东" in tail,
            }
        )
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    ignored_person_labels = {
        "序号", "股东", "持股比例", "认缴金额", "认缴出资日期", "最终受益股份",
        "控股股东", "实际控制人", "大股东", "自然人股东",
        "股权出质", "股权质押", "最终受益人",
    }
    for index, line in enumerate(lines):
        ratio_match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
        if not ratio_match:
            continue
        window = lines[max(0, index - 8):index]
        window_text = "\n".join(window)
        ratio_value = float(ratio_match.group(1))
        if any(
            item.get("type") == "company"
            and item.get("name") in window_text
            and float(item.get("ratio") or 0) == ratio_value
            for item in shareholders
        ):
            continue
        person_name = ""
        for candidate in reversed(window):
            compact = re.sub(r"\s+", "", candidate)
            if compact in ignored_person_labels or compact in seen:
                continue
            if re.fullmatch(r"[\u4e00-\u9fff·]{2,6}", compact):
                person_name = compact
                break
        if not person_name:
            continue
        seen.add(person_name)
        shareholders.append(
            {
                "name": person_name,
                "ratio": ratio_value,
                "type": "person",
                "controlling": any(marker in item for item in window for marker in ("控股股东", "实际控制人")),
            }
        )
    return sorted(shareholders, key=lambda item: (item["controlling"], item["ratio"]), reverse=True)


def contact_candidate_score(candidate: dict, preferred_names: list[str]) -> tuple[int, int]:
    """Rank direct company contacts without claiming an unverified phone-owner match."""
    tags = str(candidate.get("tags") or "")
    if "疑似空号" in tags:
        return (-1000, 0)
    display_name = re.sub(r"\s+", "", str(candidate.get("name") or "").split("·", 1)[0])
    compact_display = display_name.replace("*", "")
    preferred_score = 0
    match_type = ""
    for preferred in preferred_names:
        compact_preferred = re.sub(r"\s+", "", str(preferred or ""))
        if not compact_preferred:
            continue
        if display_name == compact_preferred:
            preferred_score = max(preferred_score, 300)
            match_type = "姓名完全匹配"
        elif "*" in display_name and compact_display and compact_preferred.startswith(compact_display):
            preferred_score = max(preferred_score, 220)
            match_type = "股东或法人姓氏匹配"
    candidate["match_type"] = match_type
    hot_level = int(candidate.get("hot_level") or 0)
    quality = hot_level * 20
    quality += 8 if "推荐" in tags else 0
    quality += 5 if "近期收录" in tags else 0
    quality += 3 if "年报" in tags or "招标信息" in tags else 0
    return (preferred_score + quality, -int(candidate.get("index") or 0))


def choose_contact_candidate(candidates: list[dict], preferred_names: list[str]) -> dict:
    usable = [candidate for candidate in candidates if contact_candidate_score(candidate, preferred_names)[0] >= 0]
    if not usable:
        return {}
    direct = [candidate for candidate in usable if "疑似代理记账" not in str(candidate.get("tags") or "")]
    # A bookkeeping contact is still a possible route to the company, but it
    # must never outrank a direct contact and must be visibly marked downstream.
    return max(direct or usable, key=lambda candidate: contact_candidate_score(candidate, preferred_names))


def contact_phone_value(candidate: dict) -> str:
    phone = str(candidate.get("phone") or "").strip()
    if not phone:
        return ""
    if "疑似代理记账" in str(candidate.get("tags") or ""):
        return f"{phone}（探迹标记疑似代理记账，待核验）"
    return phone


def extract_contact_candidates(driver, page_text: str, preferred_names: list[str]) -> tuple[list[dict], int]:
    """Extract all direct mobile-contact cards; related-company recommendations are excluded when mobile count is zero."""
    count_match = re.search(r"手机\s*(\d+)", page_text)
    mobile_count = int(count_match.group(1)) if count_match else 0
    if mobile_count <= 0:
        return [], mobile_count
    raw_candidates = driver.execute_script(
        """
        const phonePattern = /^1[3-9]\\d{9}$/;
        const phoneNodes = Array.from(document.querySelectorAll('body *')).filter(node => {
          const text = (node.innerText || '').trim();
          return node.children.length === 0 && phonePattern.test(text);
        });
        const rows = [];
        const seen = new Set();
        for (const phoneNode of phoneNodes) {
          let card = phoneNode.closest('._16g07');
          if (!card) {
            let current = phoneNode.parentElement;
            while (current && current !== document.body) {
              const text = (current.innerText || '').trim();
              if (text.length < 600 && current.querySelector('[title]')) { card = current; break; }
              current = current.parentElement;
            }
          }
          if (!card) continue;
          const phone = (phoneNode.innerText || '').trim();
          if (seen.has(phone)) continue;
          seen.add(phone);
          const titleNode = card.querySelector('[title]');
          const title = titleNode ? (titleNode.getAttribute('title') || titleNode.innerText || '') : '';
          const assets = Array.from(card.querySelectorAll('[style*="background-image"], img'))
            .map(node => `${node.getAttribute('style') || ''} ${node.getAttribute('src') || ''}`).join(' ');
          let hotLevel = 0;
          if (assets.includes('hot_plus')) hotLevel = 3;
          else if (assets.includes('2star_hot')) hotLevel = 2;
          else if (assets.includes('hot')) hotLevel = 1;
          rows.push({phone, name: title.split('·')[0].trim(), title: title.trim(), tags: (card.innerText || '').trim(), hot_level: hotLevel});
        }
        return rows;
        """
    ) or []
    candidates = []
    for index, candidate in enumerate(raw_candidates[:mobile_count]):
        phone = str(candidate.get("phone") or "").strip()
        if not re.fullmatch(r"1[3-9]\d{9}", phone):
            continue
        title = str(candidate.get("title") or "").strip()
        candidate_name = str(candidate.get("name") or "").strip()
        if "·" not in title and candidate_name not in preferred_names:
            candidate["name"] = ""
        candidate["index"] = index
        candidates.append(candidate)
    for candidate in candidates:
        contact_candidate_score(candidate, preferred_names)
    return candidates, mobile_count


def parse_company_profile(text: str, title: str = "", detail_url: str = "") -> dict:
    """Extract company identity and ownership without mixing in project fields."""
    profile = {
        "company_name": "",
        "legal_representative": "",
        "phone": "",
        "address": "",
        "credit_code": "",
        "shareholders": parse_shareholders(text),
        "detail_url": detail_url,
        "controller_url": "",
    }
    title_name = re.split(r"\s+企业的详情页|\s+-\s+企业详情", title or "", maxsplit=1)[0].strip()
    if title_name.endswith(("有限公司", "有限责任公司", "股份有限公司")):
        profile["company_name"] = title_name
    legal = re.search(r"(?:企业法人|法定代表人)\s*[:：]?\s*([^\s\n,，]{2,12})", text)
    if legal:
        profile["legal_representative"] = re.split(r"关联|现任职|曾任职", legal.group(1), maxsplit=1)[0]
    address = re.search(r"(?:企业地址|注册地址|经营地址)\s*[:：]?\s*([^\n]{5,100})", text)
    if address:
        profile["address"] = address.group(1).strip()
    credit = re.search(r"\b([0-9A-Z]{18})\b", text)
    if credit:
        profile["credit_code"] = credit.group(1)
    return profile


def extract_detail(driver) -> dict:
    """从探迹详情页抽取字段. 返回空字符串表示未抓到."""
    from selenium.webdriver.common.by import By
    result = {
        "contact_person": "", "phone": "", "address": "",
        "main_company": "", "main_contact": "", "main_phone": "",
        "main_address": "", "investor": "", "credit_code": "",
        "relation_graph": "", "remark": "",
    }
    time.sleep(2)
    detail_url = driver.current_url
    detail_title = driver.title
    basic_text = driver.execute_script("return document.body.innerText") or ""
    if not unlock_company(driver):
        result = {
            "contact_person": "", "phone": "", "address": "",
            "main_company": "", "main_contact": "", "main_phone": "",
            "main_address": "", "investor": "", "credit_code": "",
            "relation_graph": "", "remark": "解锁失败",
        }
        return result
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

    # 切到联系方式 Tab
    try:
        tab = driver.find_element(By.XPATH, "//i[contains(text(),'公司联系方式')]")
        driver.execute_script("arguments[0].parentNode.parentNode.click();", tab)
        time.sleep(2)
    except Exception:
        pass

    # Some detail pages expose the mobile count before the contact cards are
    # unlocked. Unlock once more inside the contact tab and refresh its DOM.
    unlock_company(driver)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.8)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

    if "/enterprise-details/" not in driver.current_url and "/enterprise-details/" in detail_url:
        driver.get(detail_url)
        time.sleep(2)
    text = basic_text + "\n" + (driver.execute_script("return document.body.innerText") or "")

    profile = parse_company_profile(text, detail_title, detail_url)
    legal_name = profile["legal_representative"]
    preferred_names = [
        item.get("name", "") for item in profile["shareholders"]
        if item.get("type") == "person" and item.get("controlling")
    ]
    preferred_names.extend([item.get("name", "") for item in profile["shareholders"] if item.get("type") == "person"])
    preferred_names.append(legal_name)
    contacts, mobile_count = extract_contact_candidates(driver, text, preferred_names)
    selected_contact = choose_contact_candidate(contacts, preferred_names)
    profile["phone"] = contact_phone_value(selected_contact)
    profile["contact_name"] = selected_contact.get("name", "")
    profile["contact_match"] = selected_contact.get("match_type", "")
    profile["contacts"] = contacts
    profile["mobile_count"] = mobile_count
    for link in driver.find_elements(By.CSS_SELECTOR, "a[href*='/connections-details/']"):
        try:
            if legal_name and legal_name in (link.text or ""):
                profile["controller_url"] = link.get_attribute("href") or ""
                break
        except Exception:
            continue
    result.update(
        {
            "company_name": profile["company_name"],
            "contact_person": (
                profile["contact_name"]
                if profile["phone"] and profile["contact_name"]
                else "探迹联系人（未显示姓名）"
                if profile["phone"]
                else legal_name
            ),
            "phone": profile["phone"],
            "address": profile["address"],
            "credit_code": profile["credit_code"],
            "investor": profile["shareholders"][0]["name"] if profile["shareholders"] else "",
            "shareholders": profile["shareholders"],
            "detail_url": profile["detail_url"],
            "controller_url": profile["controller_url"],
            "legal_representative": legal_name,
            "contact_match": profile["contact_match"],
            "contacts": profile["contacts"],
            "mobile_count": profile["mobile_count"],
        }
    )

    return result


def investigate_company_chain(driver, filing_company: str, timeout: int = 30) -> dict:
    """Query the filing company, then its direct controlling corporate shareholder."""
    filing_url = search_company(driver, filing_company, timeout)
    if not filing_url:
        return {}
    driver.get(filing_url)
    filing = extract_detail(driver)
    if not filing.get("company_name"):
        filing["company_name"] = filing_company

    shareholders = filing.get("shareholders") or []
    candidate_owner = next((item for item in shareholders if item.get("type") == "company"), None)
    owner = next(
        (
            item for item in shareholders
            if item.get("type") == "company"
            and (item.get("controlling") or float(item.get("ratio") or 0) > 50)
        ),
        None,
    )
    parent = {}
    if owner and owner.get("name") and owner["name"] != filing_company:
        parent_url = search_company(driver, owner["name"], timeout)
        if parent_url:
            driver.get(parent_url)
            parent = extract_detail(driver)
            if not parent.get("company_name"):
                parent["company_name"] = owner["name"]

    controlling = parent or filing
    chain = {
        "project_company": filing,
        "direct_shareholder": candidate_owner or {},
        "controlling_company": parent,
    }
    filing_name = filing.get("company_name") or filing_company
    owner_name = (candidate_owner or {}).get("name", "")
    owner_ratio = (candidate_owner or {}).get("ratio", "")
    parent_name = parent.get("company_name", "")
    controller_shareholder = next(
        (item for item in controlling.get("shareholders", []) if item.get("type") == "person" and item.get("controlling")),
        None,
    )
    controller = (controller_shareholder or {}).get("name", "") or controlling.get("legal_representative", "") or controlling.get("contact_person", "")
    fuzzy_match = normalize_company_name_for_match(filing_name) != normalize_company_name_for_match(filing_company)
    equity_lines = [f"备案项目单位：{filing_name}"]
    if fuzzy_match:
        equity_lines.append(f"探迹模糊匹配：原查询“{filing_company}” → 命中“{filing_name}”（需人工核验是否为更名或同一主体）")
    if owner_name:
        ratio_text = f"（持股 {owner_ratio:g}%）" if isinstance(owner_ratio, (int, float)) else ""
        control_note = "" if owner else "（未达到控股认定条件，仅作为一级股东候选）"
        equity_lines.append(f"一级股东：{owner_name}{ratio_text}{control_note}")
    if parent_name:
        equity_lines.append(f"背后控股公司：{parent_name}")
    if controller:
        equity_lines.append(f"关键决策人：{controller}（探迹显示为法定代表人/主要负责人，实际控制关系需人工复核）")
    equity_lines.append("核验说明：以上为探迹工商页当前可见股东链，不等同于已确认的最终实际控制人；请结合股东详情和电话反馈复核。")
    selected_contact = controlling.get("contact_person", "")
    contact_match = controlling.get("contact_match", "")
    contact_note = ""
    if controlling.get("mobile_count", 0) <= 0:
        contact_note = "探迹该企业手机联系人为0；关联公司推荐号码未写入"
    elif controlling.get("phone"):
        warning = "；该号码被探迹标记为疑似代理记账，仅作为候选联系路径" if "疑似代理记账" in controlling.get("phone", "") else ""
        contact_note = f"已选联系人：{selected_contact or '未显示姓名'}，排序依据：{contact_match or 'HOT等级及联系人质量'}{warning}"
    if contact_note:
        equity_lines.append(f"联系方式：{contact_note}")
    return {
        "project_company_address": filing.get("address", ""),
        "project_company_contact": filing.get("contact_person", ""),
        "project_company_phone": filing.get("phone", ""),
        "project_company_contacts": filing.get("contacts", []),
        "project_company_mobile_count": filing.get("mobile_count", 0),
        "project_company_credit_code": filing.get("credit_code", ""),
        "project_company_query": filing_company,
        "project_company_match": filing_name if fuzzy_match else "",
        "main_company": controlling.get("company_name", ""),
        "main_contact": controlling.get("contact_person", "") or controller,
        "main_phone": controlling.get("phone", ""),
        "main_contacts": controlling.get("contacts", []),
        "main_mobile_count": controlling.get("mobile_count", 0),
        "main_address": controlling.get("address", ""),
        "investor": candidate_owner.get("name", "") if candidate_owner else "",
        "relation_graph": "\n".join(equity_lines),
        "relation_graph_raw": chain,
        "remark": "；".join(item for item in [
            "探迹股权链：项目单位 → 控股法人股东 → 控股公司负责人" if owner else "探迹未确认控股法人股东，低持股比例股东未升级为控股公司",
            contact_note,
            "手机号与股东身份需员工电话核验",
        ] if item),
    }


def fetch_pending(conn, limit, source=None) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if source:
        cur.execute("""
            SELECT * FROM companies
            WHERE source = ? AND (contact_person = '' OR contact_person IS NULL OR phone = '' OR phone IS NULL)
            ORDER BY id DESC LIMIT ?
        """, (source, limit))
    else:
        cur.execute("""
            SELECT * FROM companies
            WHERE (contact_person = '' OR contact_person IS NULL OR phone = '' OR phone IS NULL)
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    return [dict(r) for r in cur.fetchall()]


def update_record(conn, name: str, data: dict) -> int:
    cur = conn.cursor()
    fields = ["contact_person", "phone", "address", "main_company",
              "main_contact", "main_phone", "main_address", "investor",
              "credit_code", "relation_graph", "remark"]
    set_clause = ", ".join(f"{f} = COALESCE(NULLIF(?, ''), {f})" for f in fields)
    set_clause += ", source = COALESCE(NULLIF('探迹', ''), source)"
    params = [data.get(f, "") for f in fields]
    params.append(name)
    cur.execute(f"UPDATE companies SET {set_clause} WHERE company_name = ?", params)
    return cur.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description="探迹补全 (独立模块)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--source", help="只处理某 source")
    parser.add_argument("--company", help="单条")
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()

    if not DB_PATH.exists():
        log.error("DB 不存在")
        return 1

    driver = attach_driver(DEBUG_PORT, PROFILE_DIR)
    if not is_logged_in(driver):
        if not wait_manual_login(driver):
            return 1

    driver.get(TUNGEE_SEARCH)
    time.sleep(4)

    conn = sqlite3.connect(str(DB_PATH))
    if args.company:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE company_name LIKE ?",
                    (f"%{args.company}%",))
        targets = [dict(r) for r in cur.fetchall()]
    else:
        targets = fetch_pending(conn, args.limit, args.source)
    log.info("待处理: %d 条", len(targets))

    updated = 0
    for i, row in enumerate(targets, 1):
        name = row["company_name"]
        log.info("[%d/%d] %s", i, len(targets), name[:30])
        url = search_company(driver, name)
        if not url:
            log.warning("  未找到")
            time.sleep(args.interval)
            continue
        driver.get(url)
        data = extract_detail(driver)
        log.info("  法人: %s | 电话: %s | 地址: %s",
                 data["contact_person"] or "-",
                 data["phone"] or "-",
                 (data["address"] or "-")[:30])
        if update_record(conn, name, data) > 0:
            updated += 1
            log.info("  >> 已更新")
        conn.commit()
        time.sleep(args.interval)

    conn.close()
    log.info("=" * 50)
    log.info("本次更新: %d / %d 条", updated, len(targets))
    log.info("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
