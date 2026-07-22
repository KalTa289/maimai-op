from playwright.async_api import async_playwright
from pathlib import Path
import asyncio
import json

username = "kalta"  # input("Enter the username: ")
filepath = Path("data/player_data.json")
with open("data/versions.json", "r", encoding="utf-8") as f:
    versions = json.load(f)

concurrent_tasks = 5
sem = asyncio.Semaphore(concurrent_tasks)  # limit concurrent tasks to avoid overwhelming the server

async def scrape_data(page):
    row_selector = "tr.chakra-table__row"
    await page.wait_for_selector(row_selector, timeout=10000)
    
    elements = await page.locator(row_selector).all()
    data = []

    for el in elements:
        text = await el.inner_text()
        if text.strip():
            items = [line.strip() for line in text.split("\n") if line.strip()]
            data.append(items)
    return data

def clean_data(data):
    clean_data = []
    allowed_badges = {"FC", "FC+", "AP", "AP+"}
    for row in data:
        # skip empty arrays
        if not row:
            print("Skipped empty row")
            continue
            
        head = row[0].split("\t")
        # handle unexpected row format
        if len(head) < 3:
            if head[0] == "12.8" or head[1] == "12.8":
                title = "Kisaragi"
                print(f"Kisaragi handled correctly.")
            else:
                print(f"Skipped bad head: {row}")
                continue
        elif len(head) == 4:
            level = head[1]
            chart_type = head[2]
            title = head[3]
        else:
            level = head[0]
            chart_type = head[1]
            title = head[2]
        if "%" not in row[-1] or "\t" not in row[-1]:
            played = False
        elif row[-1]:
            tail = row[-1].split("\t")
            rating = tail[0]
            percent = tail[1]
            raw_badges = row[2:-1]
            lamps = [b for b in raw_badges if b in allowed_badges]
            lamp = lamps[0] if lamps else None
            played = True
        else:
            played = False
        
        clean_data.append(
            {
            "title": title,
            "level": level,
            "type": chart_type,
            "played": played,
            "lamp": lamp,
            "rating": rating,
            "percent": percent
            } if played else {
            "title": title,
            "level": level,
            "type": chart_type,
            "played": played,
            }
        )

    return clean_data

async def read_player_data(browser, url):
    async with sem:
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            # extract username
            # locate via profile icon image. stable.
            icon_img = page.locator("img[src*='Icon']").first
            raw_name = await icon_img.locator("+ div span").first.text_content()
            username = raw_name.strip()
            # target exact span, avoid page wrappers
            label = page.get_by_text("Play #", exact=True)
            # climb to parent div, move to next sibling div
            value_box = label.locator("..").locator("+ div")
            # extract text
            raw_text = await value_box.text_content()
            # split at '(', strip whitespace, remove comma
            play_count = raw_text.split("(")[0].strip().replace(",", "")
            user_data = {
                "username": username,
                "play_count": play_count
            }
            return user_data
        except Exception as e:
            print(f"Error on {url}: {e}")
        finally:
            # ensure page closes even if task crashes
            if not page.is_closed():
                await page.close()

async def read_version_data(browser, url, version, diff):
    data_path = f"records/{version}_{diff}.json"
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
        except Exception as e:
            print(f"Error on {url}: {e}")
        finally:
            # ensure page closes even if task crashes
            if not page.is_closed():
                await page.close()
        print(f"{version}_{diff} completed.")
    return None

async def main():
    tasks = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        print(f"Fetching data for {username}")
        player_data = await read_player_data(browser, f"https://maimai.shiftpsh.com/en/profile/{username}")
        if filepath.exists() and filepath.stat().st_size > 0:
            print("Existing player data found. Checking for changes...")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except json.decoder.JSONDecodeError:
                existing_data = [] # default fallback
            if existing_data == player_data:
                print("Player data unchanged. Checking for missing version data...")
                for versionindex in range(len(versions)):
                    file_path_master = f"records/{versions[versionindex]}_MASTER.json"
                    file_path_remaster = f"records/{versions[versionindex]}_RE_MASTER.json"
                    if Path(file_path_master).exists():
                        print(f"{versions[versionindex]} MASTER - Found")
                    else:
                        print(f"{versions[versionindex]} MASTER - Missing")
                        tasks.append(read_version_data(browser, f'https://maimai.shiftpsh.com/en/profile/{username}/records?v="{versionindex}"&difficulty=MASTER&sort=level&order=desc&n=false', versions[versionindex], "MASTER"))
                    if Path(file_path_remaster).exists():
                        print(f"{versions[versionindex]} RE:MASTER - Found")
                    else:
                        print(f"{versions[versionindex]} RE:MASTER - Missing")
                        tasks.append(read_version_data(browser, f'https://maimai.shiftpsh.com/en/profile/{username}/records?v="{versionindex}"&difficulty=RE_MASTER&sort=level&order=desc&n=false', versions[versionindex], "RE_MASTER"))
            else:
                print("Player data has changed. Updating...")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(player_data, f, indent=2, ensure_ascii=False)
                for versionindex in range(len(versions)):
                    for diff in ["MASTER", "RE_MASTER"]:
                        url = f'https://maimai.shiftpsh.com/en/profile/{username}/records?v="{versionindex}"&difficulty={diff}&sort=level&order=desc&n=false'
                        tasks.append(read_version_data(browser, url, versions[versionindex], diff))
        else:
            print("No existing player data found. Fetching all data.")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(player_data, f, indent=2, ensure_ascii=False)
            for versionindex in range(len(versions)):
                for diff in ["MASTER", "RE_MASTER"]:
                    url = f'https://maimai.shiftpsh.com/en/profile/{username}/records?v="{versionindex}"&difficulty={diff}&sort=level&order=desc&n=false'
                    tasks.append(read_version_data(browser, url, versions[versionindex], diff))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()
    return results

asyncio.run(main())