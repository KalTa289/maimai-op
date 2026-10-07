import re
import html
import json
import csv
import io
import unicodedata
import requests
from pathlib import Path

SGIMERA_DATA_URL = "https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/maidx_in_lv_data_circleplus.js"
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1JXFhqpow60lXYzETOXaqIRVIaIpWWxCsGCcE0piLLDw/export?format=csv&gid=859834814"
TEMPLATE_FILE = Path("data/charts_template.json")

DIFF_NAMES = ["BASIC", "ADVANCED", "EXPERT", "MASTER", "RE_MASTER"]

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

def fetch_sgimera_constants() -> dict:
    """Parses chart constants from sgimera RatingAnalyzer (CiRCLE PLUS)."""
    try:
        res = requests.get(SGIMERA_DATA_URL, timeout=15)
        if res.status_code != 200:
            return {}
        js_text = res.text
    except Exception as e:
        print(f"[song_manager] Warning: Failed to fetch sgimera constants: {e}")
        return {}

    results = {}
    for lvl in range(15, 4, -1):
        var_name = f"lv{lvl}_rslt"
        m = re.search(rf'const\s+{var_name}\s*=\s*(\[\s*\[.*?\]\s*\]);', js_text, re.DOTALL)
        if not m:
            continue
        raw_json = re.sub(r',\s*\]', ']', m.group(1).strip())
        try:
            data = json.loads(raw_json)
        except Exception:
            continue

        for idx, sublist in enumerate(data):
            dec = 0.0 if lvl == 15 else round(0.9 - (idx * 0.1), 1)
            constant_val = round(lvl + dec, 1)
            for item in sublist:
                clean_text = re.sub(r'<[^>]+>', '', item).strip()
                clean_title = re.sub(r'^[★▲◆■●]\s*', '', clean_text).strip()
                c_type = "DX" if "[dx]" in clean_title.lower() or "[dx]" in item.lower() else "Standard"
                clean_title = re.sub(r'\[dx\]', '', clean_title, flags=re.I).strip()

                diff = "MASTER"
                if "wk_r" in item or "waku_rem" in item:
                    diff = "RE_MASTER"
                elif "wk_m" in item or "wk_m_n" in item or "waku_mas" in item:
                    diff = "MASTER"
                elif "wk_e" in item or "waku_exp" in item:
                    diff = "EXPERT"
                elif "wk_a" in item or "waku_adv" in item:
                    diff = "ADVANCED"
                elif "wk_b" in item or "waku_bas" in item:
                    diff = "BASIC"

                norm_t = normalize_title(clean_title)
                results[(norm_t, c_type, diff)] = f"{constant_val:.1f}"
    return results

def fetch_sheet_constants() -> dict:
    """Parses chart constants from Google Sheet for newly added CiRCLE PLUS songs."""
    try:
        res = requests.get(GOOGLE_SHEET_CSV_URL, timeout=15)
        if res.status_code != 200:
            return {}
        reader = list(csv.reader(io.StringIO(res.text)))
    except Exception as e:
        print(f"[song_manager] Warning: Failed to fetch Google Sheet constants: {e}")
        return {}

    diff_map = {"MAS": "MASTER", "ReMAS": "RE_MASTER", "EXP": "EXPERT", "ADV": "ADVANCED", "BAS": "BASIC"}
    results = {}

    for row in reader[9:]:
        for col_start in range(0, len(row), 6):
            if col_start + 4 < len(row):
                t = row[col_start].strip()
                c_type_raw = row[col_start+1].strip()
                diff_raw = row[col_start+2].strip()
                constant_str = row[col_start+4].strip()
                if t and constant_str and not t.startswith("＜") and "ちほー" not in t and "追加曲" not in t:
                    try:
                        c_val = float(constant_str)
                        diff = diff_map.get(diff_raw, diff_raw)
                        c_type = "DX" if c_type_raw.upper() == "DX" else "Standard"
                        norm_t = normalize_title(t)
                        results[(norm_t, c_type, diff)] = f"{c_val:.1f}"
                    except ValueError:
                        pass
    return results

def get_version_name_from_code(ver_code: int) -> str:
    """Converts official SEGA version integer codes to maimai version names."""
    if ver_code < 11000: return "maimai"
    if ver_code < 12000: return "maimai PLUS"
    if ver_code < 13000: return "GreeN"
    if ver_code < 14000: return "GreeN PLUS"
    if ver_code < 15000: return "ORANGE"
    if ver_code < 16000: return "ORANGE PLUS"
    if ver_code < 17000: return "PiNK"
    if ver_code < 18000: return "PiNK PLUS"
    if ver_code < 18500: return "MURASAKi"
    if ver_code < 19000: return "MURASAKi PLUS"
    if ver_code < 19500: return "MiLK"
    if ver_code < 19900: return "MiLK PLUS"
    if ver_code < 20000: return "FiNALE"
    if ver_code < 20500: return "DX"
    if ver_code < 21000: return "DX PLUS"
    if ver_code < 21500: return "Splash"
    if ver_code < 22000: return "Splash PLUS"
    if ver_code < 22500: return "UNiVERSE"
    if ver_code < 23000: return "UNiVERSE PLUS"
    if ver_code < 23500: return "FESTiVAL"
    if ver_code < 24000: return "FESTiVAL PLUS"
    if ver_code < 24500: return "BUDDiES"
    if ver_code < 25000: return "BUDDiES PLUS"
    if ver_code < 25500: return "PRiSM"
    if ver_code < 26000: return "PRiSM PLUS"
    if ver_code < 26500: return "CiRCLE"
    return "CiRCLE PLUS"

def fetch_sega_song_versions() -> dict:
    """Fetches song release versions from official International SEGA database (maimai.sega.com) and archives."""
    song_versions = {}
    
    # 1. Official International SEGA songs JSON
    intl_url = "https://maimai.sega.com/assets/data/maimai_songs.json"
    try:
        res = requests.get(intl_url, timeout=12)
        if res.status_code == 200:
            for s in res.json():
                t = normalize_title(s.get("title", ""))
                v_raw = s.get("version", 0)
                try:
                    v_code = int(v_raw)
                    if t:
                        song_versions[t] = get_version_name_from_code(v_code)
                except ValueError:
                    pass
    except Exception as e:
        print(f"[song_manager] Warning: Failed to fetch International SEGA songs database: {e}")

    # 2. Fallback to Japanese portal for any missing track
    if len(song_versions) < 1000:
        try:
            res = requests.get("https://maimai.sega.jp/data/maimai_songs.json", timeout=12)
            if res.status_code == 200:
                for s in res.json():
                    t = normalize_title(s.get("title", ""))
                    v_raw = s.get("version", 0)
                    try:
                        v_code = int(v_raw)
                        if t and t not in song_versions:
                            song_versions[t] = get_version_name_from_code(v_code)
                    except ValueError:
                        pass
        except Exception:
            pass

    dx_versions = [
        ('DX PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_dxplus.js'),
        ('Splash', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_splash.js'),
        ('Splash PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_splashplus.js'),
        ('UNiVERSE', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_universe.js'),
        ('UNiVERSE PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_universeplus.js'),
        ('FESTiVAL', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_festival.js'),
        ('FESTiVAL PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_festivalplus.js'),
        ('BUDDiES', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_buddies.js'),
        ('BUDDiES PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_buddiesplus.js'),
        ('PRiSM', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_prism.js'),
        ('PRiSM PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/old/maidx_in_lv_data_prismplus.js'),
        ('CiRCLE', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/maidx_in_lv_data_circle.js'),
        ('CiRCLE PLUS', 'https://sgimera.github.io/mai_RatingAnalyzer/scripts_maimai/maidx_in_lv_data_circleplus.js'),
    ]

    seen_songs = set(song_versions.keys())
    for ver_name, url in dx_versions:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                titles = re.findall(r'<span[^>]*>(.*?)</span>', r.text)
                for raw in titles:
                    clean = re.sub(r'^[★▲◆■●]\s*', '', raw).replace('[dx]', '').strip()
                    norm = normalize_title(clean)
                    if norm and norm not in seen_songs:
                        song_versions[norm] = ver_name
                        seen_songs.add(norm)
        except Exception:
            pass

    return song_versions

def disp_to_val(disp: str) -> str:
    if not disp:
        return "1.0"
    d = disp.replace("Lv", "").replace("LV", "").strip()
    if d.endswith("+"):
        try:
            return f"{float(d[:-1]) + 0.7:.1f}"
        except Exception:
            return "1.0"
    try:
        return f"{float(d):.1f}"
    except Exception:
        return "1.0"

def update_song_database() -> list:
    """
    1. Fetches all songs and their respective versions from maimai NET/SEGA database across all 5 difficulties.
    2. Uses Sgimera and Google Sheets to verify and update chart constants.
    Saves the verified master template to data/charts_template.json.
    """
    print("[song_manager] Updating songs, versions, and chart constants across all difficulties...")

    # 1. Fetch official song versions & songs list from SEGA
    song_versions = fetch_sega_song_versions()

    # 2. Fetch verified chart constants from Sgimera & Google Sheet
    sgimera_constants = fetch_sgimera_constants()
    sheet_constants = fetch_sheet_constants()
    constants_map = {**sgimera_constants, **sheet_constants}

    # Fetch official International songs database (with fallback to JP)
    raw_songs = []
    try:
        res = requests.get("https://maimai.sega.com/assets/data/maimai_songs.json", timeout=12)
        if res.status_code == 200:
            raw_songs = res.json()
    except Exception as e:
        print(f"[song_manager] Warning: Failed to fetch International songs: {e}")

    if not raw_songs:
        try:
            res = requests.get("https://maimai.sega.jp/data/maimai_songs.json", timeout=12)
            if res.status_code == 200:
                raw_songs = res.json()
        except Exception:
            pass

    master_charts = []
    existing_keys = set()

    for s in raw_songs:
        t = normalize_title(s.get("title", ""))
        if not t:
            continue
        v_raw = s.get("version", 0)
        try:
            v_code = int(v_raw)
            default_ver = get_version_name_from_code(v_code)
        except ValueError:
            default_ver = "CiRCLE PLUS"
        ver = song_versions.get(t, default_ver)

        # Standard charts (BASIC, ADVANCED, EXPERT, MASTER, RE_MASTER)
        for diff, k in [("BASIC", "lev_bas"), ("ADVANCED", "lev_adv"), ("EXPERT", "lev_exp"), ("MASTER", "lev_mas"), ("RE_MASTER", "lev_remas")]:
            if k in s and s[k]:
                key = (t, "Standard", diff)
                lvl = constants_map.get(key, disp_to_val(s[k]))
                master_charts.append({
                    "title": t,
                    "level": lvl,
                    "type": "Standard",
                    "version": ver,
                    "diff": diff
                })
                existing_keys.add(key)

        # DX charts (BASIC, ADVANCED, EXPERT, MASTER, RE_MASTER)
        for diff, k in [("BASIC", "dx_lev_bas"), ("ADVANCED", "dx_lev_adv"), ("EXPERT", "dx_lev_exp"), ("MASTER", "dx_lev_mas"), ("RE_MASTER", "dx_lev_remas")]:
            if k in s and s[k]:
                key = (t, "DX", diff)
                lvl = constants_map.get(key, disp_to_val(s[k]))
                master_charts.append({
                    "title": t,
                    "level": lvl,
                    "type": "DX",
                    "version": ver,
                    "diff": diff
                })
                existing_keys.add(key)

    # Add any remaining verified charts from constants_map
    for (t, c_type, diff), lvl in constants_map.items():
        if (t, c_type, diff) not in existing_keys:
            ver = song_versions.get(t, "CiRCLE PLUS")
            master_charts.append({
                "title": t,
                "level": lvl,
                "type": c_type,
                "version": ver,
                "diff": diff
            })
            existing_keys.add((t, c_type, diff))

    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = TEMPLATE_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(master_charts, f, indent=2, ensure_ascii=False)
    temp_file.replace(TEMPLATE_FILE)

    print(f"[song_manager] Master database saved: {len(master_charts)} charts across all 5 difficulties.")
    return master_charts

if __name__ == "__main__":
    update_song_database()
