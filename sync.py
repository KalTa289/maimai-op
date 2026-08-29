from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pathlib import Path
import asyncio
import json
import sys
from calculate import calculate_for_user, load_json

concurrent_tasks = 5
sem = asyncio.Semaphore(concurrent_tasks)

async def scrape_data(page):
    row_selector = "tr.chakra-table__row"
    await page.wait_for_selector(row_selector, timeout=10000)
    return await page.evaluate('''() => {
        const rows = Array.from(document.querySelectorAll("tr.chakra-table__row"));
        return rows.map(tr => {
            const tds = Array.from(tr.querySelectorAll("td"));
            return tds.map(td => td.innerText.trim());
        });
    }''')

def clean_data(data):
    clean = []
    allowed_badges = {"FC", "FC+", "AP", "AP+"}
    for row in data:
        if len(row) < 9:
            continue
            
        level = row[1]
        chart_type = row[2]
        raw_title = row[3]
        title = raw_title if raw_title else "\u200b"
        
        lamp_raw = row[5]
        lamp = lamp_raw if lamp_raw in allowed_badges else None
        rating = row[7] or "0"
        percent = row[8]
        played = bool(percent and "%" in percent)
        
        row_dict = {
            "title": title,
            "level": level,
            "type": chart_type,
            "played": played,
        }
        if played:
            row_dict.update({"lamp": lamp, "rating": rating, "percent": percent})
        clean.append(row_dict)

    return clean

async def read_player_data(browser, url):
    async with sem:
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            icon_img = page.locator("img[src*='Icon']").first
            raw_name = await icon_img.locator("+ div span").first.text_content()
            label = page.get_by_text("Play #", exact=True)
            value_box = label.locator("..").locator("+ div")
            raw_text = await value_box.text_content()
            return {
                "username": raw_name.strip(),
                "play_count": raw_text.split("(")[0].strip().replace(",", "")
            }
        except Exception as e:
            print(f"Error on {url}: {e}")
        finally:
            await page.close()

async def read_version_data(browser, url, user_dir, version, diff):
    data_path = user_dir / "records" / f"{version}_{diff}.json"
    async with sem:
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.locator("button:has(svg.tabler-icon-list)").click()
            await page.wait_for_timeout(3000)
            data = await scrape_data(page)
            clean_data_list = clean_data(data)
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(clean_data_list, f, indent=2, ensure_ascii=False)
        except PlaywrightTimeoutError:
            print(f"Failed to load {version} {diff}.")
        except Exception as e:
            print(f"Error on {url}: {e}")
        finally:
            await page.close()
        print(f"{version}_{diff} completed.")
    return None

async def run_sync(user_id: str = "kalta"):
    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)

    versions = load_json("data/versions.json", [])
    history = load_json(user_dir / "history.json", [])

    existing_play_count = None
    existing_username = None
    if history:
        last_snap = history[-1]
        existing_play_count = last_snap.get("play_count")
        existing_username = last_snap.get("username")

    tasks = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print(f"Fetching data for profile '{user_id}'")
        player_data = await read_player_data(browser, f"https://maimai.shiftpsh.com/en/profile/{user_id}")
        
        has_changed = True
        if player_data:
            if existing_play_count is not None and existing_play_count == player_data.get("play_count") and existing_username == player_data.get("username"):
                has_changed = False

        if has_changed:
            print(f"Player data updated/changed for @{user_id} (Play count: {player_data.get('play_count')}). Updating records...")
        else:
            print(f"Play count unchanged ({existing_play_count}). Checking for any missing version data...")

        for v_idx, version in enumerate(versions):
            for diff in ["MASTER", "RE_MASTER"]:
                diff_label = diff.replace("_", ":")
                rec_path = records_dir / f"{version}_{diff}.json"
                if not has_changed and rec_path.exists():
                    print(f"{version} {diff_label} - Found")
                else:
                    if not has_changed:
                        print(f"{version} {diff_label} - Missing")
                    url = f'https://maimai.shiftpsh.com/en/profile/{user_id}/records?v="{v_idx}"&difficulty={diff}&sort=level&order=desc&n=false'
                    tasks.append(read_version_data(browser, url, user_dir, version, diff))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    print(f"Sync complete for @{user_id}. Running calculation...")
    calculate_for_user(user_id, player_data=player_data)
    return results

if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else "kalta"
    asyncio.run(run_sync(target_user))