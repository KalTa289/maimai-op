import re
import json
import asyncio
from pathlib import Path
import requests

from calculate import calculate_for_user, load_json

BASE_URLS = {
    "intl": {
        "net": "https://maimaidx-eng.com/maimai-mobile",
        "domain": "maimaidx-eng.com",
        "site_id": "maimaidxex"
    },
    "jp": {
        "net": "https://maimaidx.jp/maimai-mobile",
        "domain": "maimaidx.jp",
        "site_id": "maimaidx"
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

# ==========================================
# 1. SEGA maimai DX NET Direct Sync Engine
# ==========================================

def calc_single_rating(level_constant: float, achievement: float) -> int:
    score = min(achievement, 100.5)
    if score >= 100.5:
        mult = 22.4
    elif score >= 100.0:
        mult = 21.6
    elif score >= 99.5:
        mult = 21.1
    elif score >= 99.0:
        mult = 20.8
    elif score >= 98.0:
        mult = 20.3
    elif score >= 97.0:
        mult = 20.0
    elif score >= 94.0:
        mult = 16.8
    elif score >= 90.0:
        mult = 15.2
    elif score >= 80.0:
        mult = 13.6
    elif score >= 75.0:
        mult = 12.0
    elif score >= 70.0:
        mult = 11.2
    elif score >= 60.0:
        mult = 9.6
    elif score >= 50.0:
        mult = 8.0
    else:
        mult = 0.0
    return int(level_constant * (score / 100.0) * mult)

def parse_cookie_input(cookie_input: str) -> dict:
    cookie_str = cookie_input.strip()
    cookies = {}
    if "=" in cookie_str:
        for p in cookie_str.split(";"):
            if "=" in p:
                k, v = p.strip().split("=", 1)
                cookies[k.strip()] = v.strip()
    else:
        # User passed a raw token string (e.g. 64-char clal or _t)
        cookies["clal"] = cookie_str
        cookies["CLAL"] = cookie_str
        cookies["_t"] = cookie_str
    return cookies

def parse_player_data(html_text: str) -> dict:
    name_m = re.search(r'<div class="name_block[^>]*>(.*?)</div>', html_text, re.DOTALL)
    username = name_m.group(1).strip() if name_m else "Unknown"

    rating_m = re.search(r'<div class="rating_block[^>]*>(.*?)</div>', html_text, re.DOTALL)
    rating = rating_m.group(1).strip() if rating_m else "0"

    play_m = re.search(r'(?:total play count|累計プレイ回数)[：:]\s*([0-9,]+)', html_text, re.IGNORECASE)
    play_count = play_m.group(1).replace(",", "").strip() if play_m else "0"

    return {
        "username": username,
        "rating": rating,
        "play_count": play_count
    }

import html

def normalize_title(raw_title: str) -> str:
    if not raw_title:
        return "\u200b"
    t = html.unescape(raw_title).strip()
    if not t:
        return "\u200b"
    # Normalize common quote variations
    t = t.replace("’", "'").replace("‘", "'").replace("”", '"').replace("“", '"')
    return t

def parse_song_cards(html_text: str) -> dict:
    songs = {}
    for form in re.finditer(r'<form[^>]*>.*?</form>', html_text, re.DOTALL):
        f_content = form.group(0)

        title_m = re.search(r'<div class="music_name_block[^>]*>(.*?)</div>', f_content, re.DOTALL)
        raw_title = title_m.group(1).strip() if title_m else ""
        title = normalize_title(raw_title)

        is_dx = bool("music_dx.png" in f_content or "music_kind_icon" in f_content)
        chart_type = "DX" if is_dx else "Standard"

        score_matches = re.findall(r'<div class="music_score_block[^>]*>(.*?)</div>', f_content, re.DOTALL)
        played = False
        percent = "0%"
        achieve_val = 0.0

        for s in score_matches:
            s_clean = s.strip()
            if "%" in s_clean:
                played = True
                percent = s_clean
                try:
                    achieve_val = float(s_clean.rstrip("%"))
                except ValueError:
                    pass
                break

        lamp = None
        if "music_icon_app.png" in f_content or "icon_app.png" in f_content:
            lamp = "AP+"
        elif "music_icon_ap.png" in f_content or "icon_ap.png" in f_content:
            lamp = "AP"
        elif "music_icon_fcp.png" in f_content or "icon_fcp.png" in f_content:
            lamp = "FC+"
        elif "music_icon_fc.png" in f_content or "icon_fc.png" in f_content:
            lamp = "FC"

        songs[(title, chart_type)] = {
            "title": title,
            "type": chart_type,
            "played": played,
            "percent": percent,
            "achievement": achieve_val,
            "lamp": lamp
        }

    return songs

def update_song_constants(api_url: str = "https://www.diving-fish.com/api/maimaidxprober/music_data") -> list:
    print(f"Fetching latest chart constants from {api_url}...")
    res = requests.get(api_url, timeout=15)
    if res.status_code != 200:
        raise ConnectionError(f"Failed to fetch song constants (HTTP {res.status_code})")

    songs = res.json()
    new_template = []

    for s in songs:
        raw_title = s.get("title", "").strip()
        title = raw_title if raw_title else "\u200b"
        c_type = "DX" if s.get("type") == "DX" else "Standard"
        ver = s.get("basic_info", {}).get("from", "maimai")
        ds = s.get("ds", [])

        if len(ds) >= 4:
            new_template.append({
                "title": title,
                "level": f"{ds[3]:.1f}",
                "type": c_type,
                "version": ver,
                "diff": "MASTER"
            })

        if len(ds) >= 5:
            new_template.append({
                "title": title,
                "level": f"{ds[4]:.1f}",
                "type": c_type,
                "version": ver,
                "diff": "RE_MASTER"
            })

    out_file = Path("data/charts_template.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(new_template, f, indent=2, ensure_ascii=False)

    print(f"Updated data/charts_template.json ({len(new_template)} charts from {len(songs)} songs).")
    return new_template

def sync_sega_direct(user_id: str = "kalta", cookie_or_token: str = "", region: str = "intl") -> dict:
    """
    Directly fetches scores and player profile from SEGA maimai DX NET using a CLAL / _t token.
    """
    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)

    token_file = user_dir / "auth_token.txt"
    if not cookie_or_token:
        if token_file.exists():
            cookie_or_token = token_file.read_text(encoding="utf-8").strip()
        else:
            raise ValueError("No authentication token provided. Please enter your CLAL or _t token.")

    config = BASE_URLS.get(region, BASE_URLS["intl"])
    base_url = config["net"]
    site_id = config["site_id"]
    target_domain = config["domain"]

    cookies = parse_cookie_input(cookie_or_token)

    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = f"{base_url}/"

    # Set cookies across domains
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=target_domain)
        session.cookies.set(k, v, domain=".am-all.net")
        session.cookies.set(k, v, domain="lng-tgk-aime-gw.am-all.net")

    # If CLAL was passed, hit the Aime common_auth gateway to exchange it for _t on maimaidx-eng.com
    if "CLAL" in cookies or "clal" in cookies:
        auth_gateway_url = f"https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id={site_id}&redirect_url={base_url}/&back_url=https://maimai.sega.com/"
        try:
            session.get(auth_gateway_url, allow_redirects=True, timeout=12)
        except Exception as e:
            print(f"Auth gateway exchange note: {e}")

    # 1. Fetch and Verify Player Data
    player_url = f"{base_url}/playerData"
    res = session.get(player_url, allow_redirects=True, timeout=15)

    if "/error" in res.url.lower() or "/login" in res.url.lower() or "ERROR CODE" in res.text or "エラーコード" in res.text:
        raise ValueError("SEGA session expired or invalid token.\n\nPlease log in on maimaidx-eng.com (or lng-tgk-aime-gw.am-all.net) and copy your CLAL or _t token.")

    if "name_block" not in res.text:
        raise ValueError(f"Unexpected page returned from SEGA (URL: {res.url}). Please verify your token.")

    player_data = parse_player_data(res.text)
    token_file.write_text(cookie_or_token, encoding="utf-8")

    # 2. Fetch Master Charts (diff=3)
    master_res = session.get(f"{base_url}/record/musicGenre/search", params={"genre": 99, "diff": 3}, timeout=25)
    master_songs = parse_song_cards(master_res.text)

    # 3. Fetch Re:Master Charts (diff=4)
    remaster_res = session.get(f"{base_url}/record/musicGenre/search", params={"genre": 99, "diff": 4}, timeout=25)
    remaster_songs = parse_song_cards(remaster_res.text)

    # 4. Load Master Charts Template
    template_path = Path("data/charts_template.json")
    if not template_path.exists():
        update_song_constants()

    template_charts = load_json(template_path, [])
    version_groups = {}
    for c in template_charts:
        key = (c["version"], c["diff"])
        version_groups.setdefault(key, []).append(c)

    # 5. Populate and Save All 54 Version Files
    for (ver_name, diff_name), charts in version_groups.items():
        diff_source = master_songs if diff_name == "MASTER" else remaster_songs
        populated_list = []

        for c in charts:
            title = c["title"]
            c_type = c["type"]
            level_str = c["level"]
            norm_t = normalize_title(title)
            scraped = diff_source.get((norm_t, c_type)) or diff_source.get((title, c_type))
            if scraped and scraped["played"]:
                level_float = float(level_str)
                achieve_pct = scraped["achievement"]
                single_rating = calc_single_rating(level_float, achieve_pct)
                row_dict = {
                    "title": title,
                    "level": level_str,
                    "type": c_type,
                    "played": True,
                    "lamp": scraped["lamp"],
                    "rating": str(single_rating),
                    "percent": scraped["percent"]
                }
            else:
                row_dict = {
                    "title": title,
                    "level": level_str,
                    "type": c_type,
                    "played": False
                }
            populated_list.append(row_dict)

        out_path = records_dir / f"{ver_name}_{diff_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(populated_list, f, indent=2, ensure_ascii=False)

    # 6. Run Overpower Calculations
    versions_data = calculate_for_user(user_id, player_data=player_data)

    return {
        "user_id": user_id,
        "player_data": player_data,
        "versions_count": len(versions_data),
        "master_count": len(master_songs),
        "remaster_count": len(remaster_songs)
    }

# ==========================================
# 2. Maishift Web Scraper (Playwright Sync)
# ==========================================

async def run_maishift_sync(user_id: str = "kalta"):
    from playwright.async_api import async_playwright
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)

    versions = load_json("data/versions.json", [])
    history = load_json(user_dir / "history.json", [])

    existing_play_count = history[-1].get("play_count") if history else None
    existing_username = history[-1].get("username") if history else None

    sem = asyncio.Semaphore(5)

    async def scrape_page_rows(page):
        await page.wait_for_selector("tr.chakra-table__row", timeout=10000)
        return await page.evaluate('''() => {
            return Array.from(document.querySelectorAll("tr.chakra-table__row")).map(tr => {
                return Array.from(tr.querySelectorAll("td")).map(td => td.innerText.trim());
            });
        }''')

    def clean_maishift_data(data):
        clean = []
        allowed_badges = {"FC", "FC+", "AP", "AP+"}
        for row in data:
            if len(row) < 9:
                continue
            level, chart_type, raw_title = row[1], row[2], row[3]
            title = raw_title if raw_title else "\u200b"
            lamp_raw = row[5]
            lamp = lamp_raw if lamp_raw in allowed_badges else None
            rating = row[7] or "0"
            percent = row[8]
            played = bool(percent and "%" in percent)
            row_dict = {"title": title, "level": level, "type": chart_type, "played": played}
            if played:
                row_dict.update({"lamp": lamp, "rating": rating, "percent": percent})
            clean.append(row_dict)
        return clean

    async def fetch_version(browser, url, v_name, diff):
        data_path = records_dir / f"{v_name}_{diff}.json"
        async with sem:
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle")
                await page.locator("button:has(svg.tabler-icon-list)").click()
                await page.wait_for_timeout(3000)
                data = await scrape_page_rows(page)
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(clean_maishift_data(data), f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error scraping {v_name} {diff}: {e}")
            finally:
                await page.close()

    tasks = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://maimai.shiftpsh.com/en/profile/{user_id}", timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        icon_img = page.locator("img[src*='Icon']").first
        raw_name = await icon_img.locator("+ div span").first.text_content()
        label = page.get_by_text("Play #", exact=True)
        raw_text = await label.locator("..").locator("+ div").text_content()
        await page.close()

        player_data = {
            "username": raw_name.strip(),
            "play_count": raw_text.split("(")[0].strip().replace(",", "")
        }

        has_changed = not (existing_play_count == player_data["play_count"] and existing_username == player_data["username"])

        for v_idx, version in enumerate(versions):
            for diff in ["MASTER", "RE_MASTER"]:
                rec_path = records_dir / f"{version}_{diff}.json"
                if has_changed or not rec_path.exists():
                    url = f'https://maimai.shiftpsh.com/en/profile/{user_id}/records?v="{v_idx}"&difficulty={diff}&sort=level&order=desc&n=false'
                    tasks.append(fetch_version(browser, url, version, diff))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    calculate_for_user(user_id, player_data=player_data)
    return player_data

# ==========================================
# 3. CLI Entry Point
# ==========================================

if __name__ == "__main__":
    import sys
    if "--update-constants" in sys.argv:
        update_song_constants()
    elif "--maishift" in sys.argv:
        target = sys.argv[2] if len(sys.argv) > 2 else "kalta"
        asyncio.run(run_maishift_sync(target))
    else:
        target = sys.argv[1] if len(sys.argv) > 1 else "kalta"
        token = sys.argv[2] if len(sys.argv) > 2 else ""
        try:
            sync_sega_direct(target, token)
        except Exception as e:
            print(f"Sync error: {e}")