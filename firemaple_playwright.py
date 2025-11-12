# -*- coding: utf-8 -*-
"""
firemaple_playwright.py
使用 Playwright 真浏览器抓取 Amazon AU 商品信息（手动修改地址版）
输出字段：链接 / 亚马逊ASIN / 价格 / 类目&排名 / 评分 / 店铺名称 / 是否FBA / review数量 / review情况
"""

import asyncio
import re
import random
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from playwright.async_api import async_playwright


# --------- 工具函数 ---------
def clean_text(txt):
    if not txt:
        return "—"
    return re.sub(r"\s+", " ", txt).strip()


# --------- 手动修改地址逻辑 ---------
async def set_au_delivery_address(page):
    """
    打开 Amazon AU 首页，等待用户手动修改收货地址。
    修改完成后按 Enter 或在命令行确认继续。
    """
    print("🔹 正在打开 Amazon AU 首页，请手动将收货地址修改为澳洲（建议邮编 2000）...")
    print("   修改完成后返回终端按 Enter 继续。")
    await page.goto("https://www.amazon.com.au/", timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    input("👉 请手动修改地址完成后按 Enter 键继续抓取...")


# --------- 商品信息提取逻辑 ---------
async def fetch_product(page, url):
    """打开商品页并解析字段（强化版：兼容旧式 Buy Box，两行文本解析）"""
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_selector("#productTitle", timeout=30000)
        await page.evaluate("window.scrollBy(0, 400)")
        await page.wait_for_timeout(1000)
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        data = {"链接": url}

        # ---------- ASIN ----------
        m = re.search(r"/dp/([A-Z0-9]{10})", url)
        data["亚马逊ASIN"] = m.group(1) if m else "—"

        # ---------- 价格 ----------
        price = None
        for sel in [
            "#corePrice_feature_div .a-price .a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "#corePrice_desktop_feature_div .a-price .a-offscreen",
            "#price_inside_buybox",
            "span.a-price .a-offscreen",
        ]:
            el = soup.select_one(sel)
            if el and "$" in el.get_text():
                price = el.get_text(strip=True)
                break
        if not price:
            for el in soup.select("span.a-offscreen"):
                parent = el.find_parent()
                pid = parent.get("id") if parent else ""
                if pid and re.search(r"(installment|emi)", pid, re.I):
                    continue
                txt = el.get_text(strip=True)
                if "$" in txt and re.search(r"\$\s?\d", txt) and len(txt) < 24:
                    price = txt
                    break
        if not price:
            whole = soup.select_one("span.a-price-whole")
            frac = soup.select_one("span.a-price-fraction")
            sym  = soup.select_one("span.a-price-symbol")
            if whole:
                price = (sym.get_text(strip=True) if sym else "$") + whole.get_text(strip=True)
                if frac:
                    price += "." + frac.get_text(strip=True)
        data["价格"] = clean_text(price)

        # ---------- 评分 ----------
        rating_el = (
            soup.select_one("span[data-hook='rating-out-of-text']")
            or soup.select_one("i[data-hook='average-star-rating'] span")
            or soup.select_one("span.a-icon-alt")
        )
        data["评分"] = clean_text(rating_el.get_text(strip=True) if rating_el else None)

        # ---------- review 数量 ----------
        rc_el = (
            soup.select_one("#acrCustomerReviewText")
            or soup.select_one("span#acrCustomerReviewText")
            or soup.select_one("[data-hook='total-review-count']")
            or soup.select_one("#acrPopover .a-size-base")
        )
        data["review数量"] = clean_text(rc_el.get_text(strip=True) if rc_el else None)

        # ---------- 店铺名称 + FBA（稳：优先取同行 <a> 文本，并做标准化去重） ----------
        def _normalize_value(s: str) -> str:
            s = clean_text(s)
            # 去掉前缀标签
            s = re.sub(r'(?i)\b(sold\s*by|ships\s*from)\b[:：]?\s*', '', s)
            # 只保留第一个“and/&”之前的卖家名（避免 "X and Y"）
            s = re.split(r'\s+(?:and|&)\s+', s, maxsplit=1, flags=re.I)[0]
            # 合并重复词（避免 "Conglin AU AU"）
            parts = s.split()
            dedup = []
            for w in parts:
                if not dedup or w != dedup[-1]:
                    dedup.append(w)
            s = " ".join(dedup)
            # 如果整串被重复两遍（"Conglin AU Conglin AU"），取前半
            mrep = re.match(r'^(?P<x>.+?)\s+\1$', s)
            if mrep:
                s = mrep.group('x')
            return s.strip(' .') or "—"

        seller = "—"
        ships_from = "—"

                # ---------- 店铺名称 + FBA（只取标签后的值，遇到停止词即截断） ----------
        seller, ships_from = "—", "—"

        def _norm(s: str) -> str:
            s = clean_text(s)
            s = re.sub(r'(?i)\b(sold\s*by|ships\s*from)\b[:：]?\s*', '', s)  # 去掉标签
            s = re.split(r'\s+(?:and|&)\s+', s, 1, flags=re.I)[0]             # 只保留 and/& 前半
            return s.strip(" .") or "—"

        # 停止词（遇到这些就认为本行结束）
        STOP_TOKENS = r"(?:\s{2,}|(?=Ships\s*from\b|Sold\s*by\b|Returns\b|Payment\b|Add to Wish List\b|Secure transaction\b|Eligible\b|Deliver to\b|Quantity\b|In stock\b)|\.\s|$)"
        SOLD_RE  = re.compile(r"Sold\s*by\s*[:：]?\s*(?P<val>.+?)"  + STOP_TOKENS, re.I | re.S)
        SHIPS_RE = re.compile(r"Ships\s*from\s*[:：]?\s*(?P<val>.+?)" + STOP_TOKENS, re.I | re.S)

        def _looks_ok(txt: str) -> bool:
            t = txt.lower()
            if not txt or len(txt) > 60: return False
            if any(k in t for k in ["returns","payment","secure transaction","add to wish list","quantity","deliver to"]):
                return False
            return True

        # A) 新版 tabular（有就直接用）
        for block in soup.select("#tabular-buybox .tabular-buybox-container, #tabular-buybox .tabular-buybox-text-row"):
            lab = block.select_one(".tabular-buybox-label")
            val = block.select_one(".tabular-buybox-text")
            if not lab or not val: continue
            label = clean_text(lab.get_text()).lower()
            value = _norm(val.get_text())
            if "sold" in label and seller == "—" and _looks_ok(value):
                seller = value
            elif "ships" in label and ships_from == "—" and _looks_ok(value):
                ships_from = value

        # B) 旧式两行文本（严格：只在该块里用“Sold by/Ships from”后的值，遇停止词截断）
        if seller == "—" or ships_from == "—":
            for box_sel in ["#shipsFromSoldBy_feature_div", "#desktop_buybox", "#rightCol", "#buybox_feature_div"]:
                box = soup.select_one(box_sel)
                if not box: 
                    continue
                txt = clean_text(box.get_text(" ", strip=True))

                if ships_from == "—":
                    m1 = SHIPS_RE.search(txt)
                    if m1:
                        v = _norm(m1.group("val"))
                        if _looks_ok(v):
                            ships_from = v

                if seller == "—":
                    m2 = SOLD_RE.search(txt)
                    if m2:
                        v = _norm(m2.group("val"))
                        if _looks_ok(v):
                            seller = v

        # C) merchant-info 兜底
        if seller == "—":
            mi = soup.select_one("#merchant-info")
            if mi:
                m = SOLD_RE.search(clean_text(mi.get_text(" ", strip=True)))
                if m:
                    v = _norm(m.group("val"))
                    if _looks_ok(v):
                        seller = v

        data["店铺名称"] = seller

        # ---------- 是否FBA ----------
        is_fba = "否"
        if ships_from != "—" and "amazon" in ships_from.lower():
            is_fba = "是"
        else:
            blob = " ".join([
                soup.select_one("#merchant-info").get_text(" ", strip=True) if soup.select_one("#merchant-info") else "",
                soup.select_one("#tabular-buybox").get_text(" ", strip=True) if soup.select_one("#tabular-buybox") else "",
                soup.select_one("#shipsFromSoldBy_feature_div").get_text(" ", strip=True) if soup.select_one("#shipsFromSoldBy_feature_div") else "",
                soup.select_one("#desktop_buybox").get_text(" ", strip=True) if soup.select_one("#desktop_buybox") else "",
            ]).lower()
            if any(k in blob for k in ["fulfilled by amazon","ships from amazon","dispatched by amazon","delivered by amazon"]):
                is_fba = "是"
        data["是否FBA"] = is_fba



        # ---------- 类目&排名 ----------
        bsr = "—"
        for sel in ["#detailBullets_feature_div", "#productDetails_detailBullets_sections1", "#prodDetails"]:
            node = soup.select_one(sel)
            if not node:
                continue
            text = node.get_text(" ", strip=True)
            mm = re.search(r"Best\s*Sellers?\s*Rank\s*:?\s*(.+?)(?:Date First Available|Customer Reviews|ASIN|$)", text, flags=re.I)
            if mm:
                bsr = clean_text(mm.group(1))
                break
        if bsr == "—":
            crumbs = [a.get_text(strip=True) for a in soup.select("#wayfinding-breadcrumbs_feature_div a")]
            if crumbs:
                bsr = " / ".join([c for c in crumbs if c])
        data["类目&排名"] = bsr

        # ---------- review 情况 ----------
        rv = (
            soup.select_one("div[data-hook='review'] span[data-hook='review-title'] span")
            or soup.select_one("div[data-hook='review'] span[data-hook='review-body'] span")
        )
        if rv:
            txt = rv.get_text(strip=True)
            data["review情况"] = clean_text(txt[:120] + ("..." if len(txt) > 120 else ""))
        else:
            data["review情况"] = "—"

        return data

    except Exception as e:
        print(f"[ERROR] {url} 抓取失败：{e}")
        return None




# --------- 主流程 ---------
async def main():
    # 读取链接
    with open("urls.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 改 True 可隐藏浏览器
        context = await browser.new_context(locale="en-AU", viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # 手动修改地址
        await set_au_delivery_address(page)

        for url in tqdm(urls, desc="抓取进度", unit="item"):
            data = await fetch_product(page, url)
            if data:
                results.append(data)
            await asyncio.sleep(2 + (random.random() * 2))

        await browser.close()

    # 输出 CSV
    if results:
        df = pd.DataFrame(
            results,
            columns=["链接", "亚马逊ASIN", "价格", "类目&排名", "评分", "店铺名称", "是否FBA", "review数量", "review情况"],
        )
        df.to_csv("firemaple_playwright.csv", index=False, encoding="utf-8-sig")
        print(f"[DONE] 共保存 {len(df)} 条商品数据到文件：firemaple_playwright.csv")
    else:
        print("[ERROR] 没有成功抓取到任何商品信息。")


if __name__ == "__main__":
    asyncio.run(main())

