#!/usr/bin/env python3
"""Pull today's VT dining menus, nutrition and hours, plus Rec Sports gym hours,
into data/dining.json for the HokieMacros app.

Runs once a day from GitHub Actions. Uses only the Python standard library.
Sources (all public, the same ones VT's own websites use):
  - FoodPro menus + nutrition: https://foodpro.students.vt.edu/menus/
  - Dining hours:              https://apps.students.vt.edu/hours/
  - Rec Sports hours:          https://apps.students.vt.edu/rshours/
"""
import html as htmllib, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
FOODPRO = "https://foodpro.students.vt.edu/menus/API"
DINING_HOURS = "https://apps.students.vt.edu/hours/Api/NonRestricted/FoodProCentersOpen/readByFoodPro/{loc}/{date}"
GYM_HOURS = "https://apps.students.vt.edu/rshours/Api/NonRestricted/UnitsOpenOnDay/Date/{date}"
GYMS = ["McComas", "McComas Pool", "War Memorial"]
MENU_DAYS = 2      # today + tomorrow
HOURS_DAYS = 8     # a week ahead, so the app can say "opens Monday"
BATCH = 100        # nutrition items per request
PAUSE = 0.25       # be gentle with VT's servers
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "dining.json")
UA = "HokieMacros/1.0 (free student app; github.com/lucakane246/hokiemacros)"

NUTRIENTS = {"Cals": "cal", "Prot": "p", "Carb": "c", "Fat-T": "f", "Fiber": "fib", "Sugar": "sug", "Sod": "sod"}


# All-you-care-to-eat door prices, from each dining center's page on dining.vt.edu
DOOR_PAGES = {"15": "https://dining.vt.edu/dining_centers/dietrick-hall.html",
              "39": "https://dining.vt.edu/dining_centers/owens.html"}


def door_prices(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ! failed {url}: {e}", file=sys.stderr)
        return None
    i = page.find("Door Entry Rates")
    if i < 0:
        return None
    table = page[i:page.find("</table>", i)]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", table, re.S):
        cells = [htmllib.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) >= 2:
            m = re.search(r"\$\s*(\d+(?:\.\d\d)?)", cells[1])
            if m:
                rows.append({"meal": cells[0], "price": float(m.group(1))})
    return rows or None


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
            time.sleep(PAUSE)
            return json.loads(body)
        except Exception as e:  # network blip or bad JSON: wait and retry
            if i == tries - 1:
                print(f"  ! failed {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (i + 1))


def num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None  # FoodPro uses "----" for unknown


def hhmm(t):
    """'09:30:01' -> '09:30'"""
    return (t or "")[:5]


def parse_hours(units):
    """Normalize either hours API's unit list into [{name, open, close, title, label}]."""
    out = []
    for u in units or []:
        for h in u.get("hours") or []:
            label = h.get("label")
            if isinstance(label, dict):
                label = label.get("name") or label.get("label")
            out.append({
                "unit": (u.get("name") or "").strip(),
                "open": hhmm(h.get("open_time")),
                "close": hhmm(h.get("close_time")),
                "title": (h.get("title") or "").strip(),
                "label": (label or "").strip(),
            })
    out.sort(key=lambda x: x["open"])
    return out


def main():
    now = datetime.now(ET)
    days = [(now + timedelta(days=i)).date() for i in range(HOURS_DAYS)]
    data = {"updated": now.isoformat(timespec="minutes"), "menuDays": [d.isoformat() for d in days[:MENU_DAYS]],
            "hoursDays": [d.isoformat() for d in days], "locations": [], "menus": {}, "items": {}, "hours": {}, "gyms": {}}

    locs = get_json(f"{FOODPRO}/Locations.aspx") or []
    print(f"{len(locs)} locations")
    for loc in locs:
        n = loc["locationNum"]
        data["locations"].append({"num": n, "name": (loc.get("name") or "").strip()})

        # menus
        data["menus"][n] = {}
        for d in days[:MENU_DAYS]:
            q = urllib.parse.urlencode({"locationNum": n, "dtdate": d.strftime("%m/%d/%Y")})
            m = get_json(f"{FOODPRO}/MenuAtLocation.aspx?{q}") or {}
            meals = []
            for meal in m.get("meals") or []:
                sections = []
                for s in meal.get("sections") or []:
                    ids = []
                    for r in s.get("recipes") or []:
                        rid = r.get("recipeId")
                        if not rid:
                            continue
                        ids.append(rid)
                        if rid not in data["items"]:
                            data["items"][rid] = {
                                "n": (r.get("name") or "").strip(),
                                "d": (r.get("description") or "").strip()[:160],
                                "s": f'{r.get("portionSize") or ""} {(r.get("portionUnit") or "").lower()}'.strip(),
                                "t": [t for t in (r.get("legendImages") or []) if t],
                                "a": (r.get("allergens") or "").strip(),
                            }
                    if ids:
                        sections.append({"name": (s.get("sectionName") or "").strip(), "items": ids})
                if sections:
                    meals.append({"meal": meal.get("mealName") or "Menu", "sections": sections})
            data["menus"][n][d.isoformat()] = meals

        # dining hours, a week ahead
        data["hours"][n] = {}
        for d in days:
            data["hours"][n][d.isoformat()] = parse_hours(get_json(DINING_HOURS.format(loc=n, date=d.isoformat())))
        print(f"  {n} {loc.get('name','').strip()}: done")

    # nutrition for every item on any menu, in batches
    ids = list(data["items"])
    print(f"nutrition for {len(ids)} items")
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        rep = get_json(f"{FOODPRO}/NutritiveReport.aspx?items=" + ",".join(f"{x}*1*1" for x in chunk)) or {}
        for r in rep.get("recipes") or []:
            item = data["items"].get(r.get("id"))
            if not item:
                continue
            for nut in r.get("nutrients") or []:
                k = NUTRIENTS.get(nut.get("name"))
                if k:
                    v = num(nut.get("value"))
                    if v is not None:
                        item[k] = round(v) if k in ("cal", "sod") else v

    # door prices at the all-you-care-to-eat halls
    data["doorPrices"] = {}
    for n, url in DOOR_PAGES.items():
        rows = door_prices(url)
        if rows:
            data["doorPrices"][n] = rows
    print(f"door prices: {data['doorPrices']}")

    # Rec Sports gyms
    for g in GYMS:
        data["gyms"][g] = {}
    for d in days:
        units = get_json(GYM_HOURS.format(date=d.isoformat())) or []
        for g in GYMS:
            data["gyms"][g][d.isoformat()] = parse_hours([u for u in units if (u.get("name") or "").strip() == g])

    have_nut = sum(1 for v in data["items"].values() if "cal" in v)
    if not data["locations"] or not data["items"]:
        print("No menu data came back; keeping the previous file.", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {OUT}: {len(data['items'])} items ({have_nut} with nutrition), {os.path.getsize(OUT)//1024} KB")


if __name__ == "__main__":
    main()
