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

def calc_max_op(title, difficulty, master_dict, remaster_dict):
    max_op = 0.0
    if difficulty == "master":
        level = float(master_dict[title]["level"])
    elif difficulty == "remaster":
        level = float(remaster_dict[title]["level"])
    max_op = (level + 3.0) * 5.0
    return max_op

def calc_op(played, level_str, lamp, rating_str, percent_str):
    op = 0.0
    if not played:
        return op
        
    level = float(level_str)
    rating = float(rating_str) / 20.0
    score = float(percent_str.strip("%"))

    combo_bonus = 0.0
    match lamp:
        case "FC":
            combo_bonus = 0.5
        case "FC+":
            combo_bonus = 0.75
        case "AP":
            combo_bonus = 1.0
        case "AP+":
            combo_bonus = 1.25
            
    if 97.0000 <= score <= 100.0000:
        op = rating * 5.0 + combo_bonus
    elif score > 100.0000:
        score_bonus = (score - 100.0000) * 3.75
        op = (level + 2.0) * 5.0 + combo_bonus + score_bonus

    return op