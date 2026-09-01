import re
import html
import json
import unicodedata
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from calculate import calculate_for_user, load_json

def is_sega_maintenance() -> bool:
    return 4 <= datetime.now(timezone(timedelta(hours=9))).hour < 7

BASE_URL = "https://maimaidx-eng.com/maimai-mobile"

SGIMERA_DATA_URL = "https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/maidx_in_lv_data_circleplus.js"
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1JXFhqpow60lXYzETOXaqIRVIaIpWWxCsGCcE0piLLDw/export?format=csv&gid=859834814"

AUTH_GATEWAY_URL = (
    "https://lng-tgk-aime-gw.am-all.net/common_auth/login"
    "?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

RATING_COEFFS = [
    (100.5, 22.4), (100.0, 21.6), (99.5, 21.1), (99.0, 20.8),
    (98.0, 20.3), (97.0, 20.0), (94.0, 16.8), (90.0, 15.2),
    (80.0, 13.6), (75.0, 12.0), (70.0, 11.2), (60.0, 9.6),
    (50.0, 8.0), (40.0, 6.4), (30.0, 4.8), (20.0, 3.2),
    (10.0, 1.6), (0.0, 0.0)
]

VERSION_MAP = {
    "maimai": "maimai", "maimai PLUS": "maimai PLUS",
    "maimai GreeN": "GreeN", "maimai GreeN PLUS": "GreeN PLUS",
    "maimai ORANGE": "ORANGE", "maimai ORANGE PLUS": "ORANGE PLUS",
    "maimai PiNK": "PiNK", "maimai PiNK PLUS": "PiNK PLUS",
    "maimai MURASAKi": "MURASAKi", "maimai MURASAKi PLUS": "MURASAKi PLUS",
    "maimai MiLK": "MiLK", "maimai MiLK PLUS": "MiLK PLUS", "MiLK PLUS": "MiLK PLUS",
    "maimai FiNALE": "FiNALE", "maimai でらっくす": "DX", "maimai でらっくす PLUS": "DX PLUS",
    "maimai でらっくす Splash": "Splash", "maimai でらっくす Splash PLUS": "Splash PLUS",
    "maimai でらっくす UNiVERSE": "UNiVERSE", "maimai でらっくす UNiVERSE PLUS": "UNiVERSE PLUS",
    "maimai でらっくす FESTiVAL": "FESTiVAL", "maimai でらっくす FESTiVAL PLUS": "FESTiVAL PLUS",
    "maimai でらっくす BUDDiES": "BUDDiES", "maimai でらっくす BUDDiES PLUS": "BUDDiES PLUS",
    "maimai でらっくす PRiSM": "PRiSM", "maimai でらっくす PRiSM PLUS": "PRiSM PLUS",
    "maimai でらっくす CiRCLE": "CiRCLE", "maimai でらっくす CiRCLE PLUS": "CiRCLE PLUS",
}

DIFF_NAMES = ["BASIC", "ADVANCED", "EXPERT", "MASTER", "RE_MASTER"]

DELETED_SONGS = {
    "二息歩行",
}

SUPPLEMENTAL_CHARTS = [
    {
        "title": "Xaleid◆scopiX",
        "type": "DX",
        "version": "PRiSM PLUS",
        "ds": [7.7, 11.0, 13.7, 14.9, 15.0]
    }
]

def calc_single_rating(level: float, achieve: float) -> int:
    cap_achieve = min(100.5, achieve)
    coeff = 0.0
    for threshold, c in RATING_COEFFS:
        if achieve >= threshold:
            coeff = c
            break
    return int(level * coeff * cap_achieve / 100.0)

def parse_cookie_input(raw_input: str) -> dict:
    raw = raw_input.strip()
    if not raw:
        return {}
    if "=" not in raw and len(raw) >= 16:
        return {"clal": raw}
    cookies = {k.strip(): v.strip().strip('"') for part in raw.split(";") if "=" in part for k, v in [part.strip().split("=", 1)]}
    return cookies if cookies else ({"clal": raw} if raw else {})

def parse_player_data(html_text: str) -> dict:
    name_m = re.search(r'<div class="name_block[^>]*>(.*?)</div>', html_text, re.DOTALL)
    raw_name = name_m.group(1).strip() if name_m else "Unknown"
    clean_name = html.unescape(re.sub(r'<[^>]+>', '', raw_name)).strip() or "Unknown"

    rating_m = re.search(r'<div class="rating_block[^>]*>(.*?)</div>', html_text, re.DOTALL)
    rating_val = int(re.sub(r'\D', '', rating_m.group(1))) if rating_m else 0

    v_play_m = re.search(r'(?:current version|今バージョン)[^\d]*([\d,]+)', html_text, re.I)
    tot_play_m = re.search(r'(?:total play count|累計プレイ回数|総プレイ回数|total play)[^\d]*([\d,]+)', html_text, re.I)

    version_plays = int(v_play_m.group(1).replace(",", "")) if v_play_m else 0
    total_plays = int(tot_play_m.group(1).replace(",", "")) if tot_play_m else 0
    total_plays, version_plays = total_plays or version_plays, version_plays or total_plays

    return {
        "username": clean_name,
        "rating": rating_val,
        "play_count": total_plays,
        "version_play_count": version_plays,
    }

def normalize_title(raw_title: str) -> str:
    if not raw_title:
        return "\u200b"
    t = html.unescape(raw_title).strip()
    if not t:
        return "\u200b"
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("’", "'").replace("‘", "'").replace("”", '"').replace("“", '"')
    t = t.replace("◇", "◆").replace("&#9670;", "◆").replace("&#9671;", "◆")
    return re.sub(r'\s+', ' ', t).strip()

def is_utage_title_or_block(title: str, block_html: str) -> bool:
    """Returns True if the song card or title corresponds to an UTAGE (宴) chart."""
    if "music_utage.png" in block_html or "music_kind_icon_utage" in block_html:
        return True
    if 'name="genre" value="199"' in block_html or 'genre=199' in block_html:
        return True
    # Match UTAGE title prefix tags: [宴], [協], [蔵], [蛸], [星], [は], [狂], [光], [即], [覚], [撫], etc.
    if re.match(r"^\[(?:宴|協|蔵|蛸|星|は|狂|光|即|覚|撫|跳|耐|疑|傾|戯|直|逆|撃|双|謎|極|超|真|弾|変)\]", title):
        return True
    return False

def parse_chart_type(block_html: str) -> str:
    """Accurately identifies if a SEGA DX NET song card is DX or Standard."""
    # 1. Primary kind icon (non-pointer)
    if re.search(r'<img[^>]*class="music_kind_icon\b(?![^"]*pointer)[^"]*"[^>]*src="[^"]*music_dx\.png"', block_html) or \
       re.search(r'<img[^>]*src="[^"]*music_dx\.png"[^>]*class="music_kind_icon\b(?![^"]*pointer)[^"]*"', block_html):
        return "DX"
    if re.search(r'<img[^>]*class="music_kind_icon\b(?![^"]*pointer)[^"]*"[^>]*src="[^"]*music_standard\.png"', block_html) or \
       re.search(r'<img[^>]*src="[^"]*music_standard\.png"[^>]*class="music_kind_icon\b(?![^"]*pointer)[^"]*"', block_html):
        return "Standard"

    # 2. Toggle pointer fallback
    # If the toggle pointer is Standard, clicking it switches to Standard, so current card is DX!
    if "music_kind_icon_standard pointer" in block_html:
        return "DX"
    if "music_kind_icon_dx pointer" in block_html:
        return "Standard"

    # 3. Simple presence fallback
    if "music_dx.png" in block_html:
        return "DX"
    return "Standard"

def level_matches(display_lvl: str, ds_val: float) -> bool:
    """Checks if a display level string from SEGA DX NET matches a chart constant float."""
    if not display_lvl:
        return True
    clean_lvl = display_lvl.strip().replace("Lv", "").replace("LV", "")
    has_plus = clean_lvl.endswith("+")
    try:
        base_int = int(clean_lvl[:-1] if has_plus else clean_lvl)
    except ValueError:
        return True

    ds_base = int(ds_val)
    ds_frac = round(ds_val - ds_base, 1)

    if base_int != ds_base:
        return False
    if base_int < 7 or base_int >= 15:
        return True
    expected_plus = (ds_frac >= 0.7)
    return has_plus == expected_plus

def parse_song_cards(html_text: str) -> list[dict]:
    songs = []
    for b in html_text.split('<div class="w_450')[1:]:
        if 'name="idx"' not in b and "music_name_block" not in b:
            continue

        title_m = re.search(r'<div class="music_name_block[^>]*>(.*?)</div>', b, re.DOTALL)
        if not title_m:
            continue
        raw_title = title_m.group(1).strip()
        title = normalize_title(raw_title)

        if is_utage_title_or_block(title, b):
            continue

        chart_type = parse_chart_type(b)

        # Extract display level if available (e.g. '12', '12+', '13')
        lv_m = re.search(r'<div class="music_lv_block[^>]*>(.*?)</div>', b, re.DOTALL)
        level_disp = lv_m.group(1).strip() if lv_m else ""

        score_matches = re.findall(r'<div class="music_score_block[^>]*>(.*?)</div>', b, re.DOTALL)
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

        lamp = next((l for icon, l in [("app", "AP+"), ("ap", "AP"), ("fcp", "FC+"), ("fc", "FC")] if f"icon_{icon}.png" in b), None)

        songs.append({
            "title": title,
            "raw_title": raw_title,
            "type": chart_type,
            "level_disp": level_disp,
            "played": played,
            "percent": percent,
            "achievement": achieve_val,
            "lamp": lamp
        })
    return songs

import song_manager

def sync_clal(user_id: str, clal: str | None = None, progress_callback = None) -> dict:
    if is_sega_maintenance():
        raise ConnectionError("SEGA maimai DX NET is currently undergoing daily server maintenance (04:00 - 07:00 JST). Sync is unavailable during this time. Please try again after 07:00 JST.")

    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)
    token_file = user_dir / "auth_token.txt"

    if not clal:
        if token_file.exists():
            clal = token_file.read_text(encoding="utf-8").strip()
        elif (records_dir / "auth_token.txt").exists():
            clal = (records_dir / "auth_token.txt").read_text(encoding="utf-8").strip()
        else:
            raise ValueError(f"No auth token provided and no saved token found for '{user_id}'.")

    cookie_dict = parse_cookie_input(clal)
    if not cookie_dict:
        raise ValueError("Invalid cookie format. Provide a 64-char CLAL token or full cookie string.")

    session = requests.Session()
    session.headers.update(HEADERS)

    for k, v in cookie_dict.items():
        session.cookies.set(k, v, domain="maimaidx-eng.com")
        session.cookies.set(k, v, domain=".am-all.net")

    if "clal" in cookie_dict or "CLAL" in cookie_dict:
        try:
            session.get(AUTH_GATEWAY_URL, allow_redirects=True, timeout=12)
        except Exception as e:
            raise ConnectionError(f"Aime gateway authentication failed: {e}")

    player_url = f"{BASE_URL}/playerData"
    res = session.get(player_url, allow_redirects=True, timeout=15)

    if "/error" in res.url.lower() or "/login" in res.url.lower() or "ERROR CODE" in res.text or "エラーコード" in res.text:
        raise ValueError("SEGA session expired or invalid token.\nPlease log in on lng-tgk-aime-gw.am-all.net and copy your CLAL token.")

    if "name_block" not in res.text:
        raise ValueError(f"Unexpected page returned from SEGA. Please verify your token.")

    player_data = parse_player_data(res.text)
    token_file.write_text(clal, encoding="utf-8")

    if progress_callback:
        progress_callback("auth", player_data, None)

    # Fetch player's scores across all 5 difficulties (5 requests total)
    diff_songs = {}
    for diff_idx, diff_name in enumerate(DIFF_NAMES):
        if progress_callback:
            progress_callback("fetching", diff_name, None)
        try:
            diff_res = session.get(
                f"{BASE_URL}/record/musicGenre/search",
                params={"genre": 99, "diff": diff_idx},
                timeout=25
            )
            cards = parse_song_cards(diff_res.text)
            diff_songs[diff_name] = cards
            if progress_callback:
                progress_callback("complete", diff_name, len(cards))
        except Exception as e:
            print(f"Warning: Failed to fetch {diff_name} records: {e}")
            diff_songs[diff_name] = []
            if progress_callback:
                progress_callback("error", diff_name, 0)

    if progress_callback:
        progress_callback("saving", None, None)

    # Ensure charts template exists
    template_file = Path("data/charts_template.json")
    if not template_file.exists():
        song_manager.update_song_database()

    template_charts = load_json(template_file, [])
    version_groups = {}
    for c in template_charts:
        version_groups.setdefault((c["version"], c["diff"]), []).append(c)

    # Populate and write user record files by version and difficulty
    for (ver_name, diff_name), charts in version_groups.items():
        scraped_list = diff_songs.get(diff_name, [])
        cards_by_key = {}
        for card in scraped_list:
            k = (card["title"], card["type"])
            cards_by_key.setdefault(k, []).append(card)

        populated_list = []
        for c in charts:
            norm_t = normalize_title(c["title"])
            c_type = c.get("type", "Standard")
            
            # Find scraped card match
            scraped = None
            candidates = cards_by_key.get((norm_t, c_type), []) or cards_by_key.get((c["title"], c_type), [])
            if candidates:
                scraped = candidates[0]
            elif scraped_list:
                # Song is absent on SEGA DX NET -> removed from game, skip
                continue

            level_str = c["level"]
            level_val = float(level_str)

            if scraped and scraped["played"]:
                single_rating = calc_single_rating(level_val, scraped["achievement"])
                row = {
                    "title": c["title"],
                    "level": level_str,
                    "type": c_type,
                    "played": True,
                    "percent": scraped["percent"],
                    "rating": str(single_rating)
                }
                if scraped.get("lamp"):
                    row["lamp"] = scraped["lamp"]
                populated_list.append(row)
            else:
                populated_list.append({
                    "title": c["title"],
                    "level": level_str,
                    "type": c_type,
                    "played": False
                })

        out_path = records_dir / f"{ver_name}_{diff_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(populated_list, f, indent=2, ensure_ascii=False)

    calculate_for_user(user_id, player_data=player_data)

    return {
        "status": "success",
        "player_data": player_data,
        "scraped_counts": {k: len(v) for k, v in diff_songs.items()},
        "versions_count": len(version_groups)
    }

sync_sega_direct = sync_clal

if __name__ == "__main__":
    import sys
    if "--update-constants" in sys.argv or "--update" in sys.argv:
        song_manager.update_song_database()
    else:
        target = sys.argv[1] if len(sys.argv) > 1 else ""
        token = sys.argv[2] if len(sys.argv) > 2 else ""
        try:
            sync_clal(target, token)
        except Exception as e:
            print(f"Sync error: {e}")