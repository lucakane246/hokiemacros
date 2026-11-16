#!/usr/bin/env python3
"""Build data/foods.json, the general food database for HokieMacros' food search.

Source: USDA FoodData Central (public domain, CC0) - https://fdc.nal.usda.gov
  - Foundation Foods : current lab-analysed basics (eggs, oils, produce ...)
  - SR Legacy        : 7,793 classic foods, incl. a "Fast Foods" group
                       (McDonald's, Burger King, Wendy's, Taco Bell, KFC, Pizza Hut ...)
  - FNDDS / Survey   : everyday dishes as people actually eat them

Runs from GitHub Actions once a month (USDA updates twice a year). Standard library only.
"""
import io, json, os, re, sys, time, urllib.request, zipfile
sys.path.insert(0, os.path.dirname(__file__))
import food_names

PAGE = "https://fdc.nal.usda.gov/download-datasets"
BASE = "https://fdc.nal.usda.gov/fdc-datasets/"
FALLBACK = {
    "foundation": "FoodData_Central_foundation_food_json_2026-10-29.zip",
    "sr": "FoodData_Central_sr_legacy_food_json_2018-04.zip",
    "survey": "FoodData_Central_survey_food_json_2024-10-31.zip",
}
PATTERN = {
    "foundation": r"FoodData_Central_foundation_food_json_[\d-]+\.zip",
    "sr": r"FoodData_Central_sr_legacy_food_json_[\d-]+\.zip",
    "survey": r"FoodData_Central_survey_food_json_[\d-]+\.zip",
}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "foods.json")
UA = "HokieMacros/1.0 (free student app; github.com/lucakane246/hokiemacros)"

# USDA nutrient numbers -> our short keys (all per 100 g)
NUTR = {"208": "cal", "203": "p", "205": "c", "204": "f", "291": "fib", "269": "sug", "307": "sod"}
ENERGY_FALLBACK = ("958", "957")  # Atwater energy, used by some Foundation foods instead of 208

SKIP_CATEGORIES = {"Baby Foods", "Infant formulas", "Human milk", "Baby food: ready-to-eat", "Baby food: cereals",
                   "Baby food: fruit", "Baby food: vegetables", "Baby food: meat and dinners", "Baby food: yogurt",
                   "Baby juice", "Baby water", "Formula, ready-to-feed", "Formula, prepared from powder",
                   "Formula, prepared from concentrate", "American Indian/Alaska Native Foods"}

BRANDS = {  # how chain names should read
    "MCDONALD'S": "McDonald's", "BURGER KING": "Burger King", "WENDY'S": "Wendy's", "TACO BELL": "Taco Bell",
    "KFC": "KFC", "PIZZA HUT": "Pizza Hut", "DOMINO'S": "Domino's", "PAPA JOHN'S": "Papa John's", "POPEYES": "Popeyes",
    "SUBWAY": "Subway", "DAIRY QUEEN": "Dairy Queen", "LITTLE CAESARS": "Little Caesars", "CHICK-FIL-A": "Chick-fil-A",
    "ARBY'S": "Arby's", "SONIC": "Sonic", "CARL'S JR.": "Carl's Jr.", "JACK IN THE BOX": "Jack in the Box",
    "APPLEBEE'S": "Applebee's", "T.G.I. FRIDAY'S": "TGI Friday's", "OLIVE GARDEN": "Olive Garden",
    "DENNY'S": "Denny's", "CRACKER BARREL": "Cracker Barrel", "CHILI'S": "Chili's", "RED LOBSTER": "Red Lobster",
    "ON THE BORDER": "On The Border", "CARRABBA'S ITALIAN GRILL": "Carrabba's", "STARBUCKS": "Starbucks",
}
KEEP_UPPER = {"KFC", "BBQ", "USDA", "NFS", "NS", "UHT", "TGI", "II", "B", "C", "D", "E", "K"}


def latest_urls():
    urls = {k: BASE + v for k, v in FALLBACK.items()}
    try:
        html = fetch(PAGE).decode("utf-8", "replace")
        for k, pat in PATTERN.items():
            found = sorted(set(re.findall(pat, html)))
            if found:
                urls[k] = BASE + found[-1]  # names end in a date, so the last sorts newest
    except Exception as e:
        print(f"! couldn't read the download page, using known files: {e}", file=sys.stderr)
    return urls


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def load_foods(url):
    print(f"downloading {url}")
    z = zipfile.ZipFile(io.BytesIO(fetch(url)))
    name = next(n for n in z.namelist() if n.endswith(".json"))
    data = json.loads(z.read(name))
    return next(v for v in data.values() if isinstance(v, list))


def tidy(name):
    """'McDONALD'S, McCHICKEN Sandwich' -> ("McDonald's", "McChicken Sandwich"); plain names untouched."""
    name = re.sub(r"\s*\(Includes foods for USDA's Food Distribution Program\)", "", name, flags=re.I)
    brand = None
    for raw, nice in BRANDS.items():
        m = re.match(re.escape(raw) + r"[,\s]+", name, flags=re.I)
        if m:
            brand, name = nice, name[m.end():].strip()
            break

    def fix(w):
        core = re.sub(r"[^A-Za-z]", "", w)
        if re.match(r"^Mc[A-Z]{2,}", w):                      # McCHICKEN -> McChicken
            return "Mc" + w[2].upper() + w[3:].lower()
        if len(core) >= 2 and core.isupper() and core not in KEEP_UPPER:
            return re.sub(r"[A-Za-z]", lambda m: m.group(0).upper(), w.lower(), count=1)
        return w

    name = " ".join(fix(w) for w in name.split(" "))
    return brand, name[:1].upper() + name[1:]


def portion_label(p):
    desc = (p.get("portionDescription") or "").strip()
    if desc and desc.lower() not in ("quantity not specified", "guideline amount per fl oz of beverage"):
        label = desc
    else:
        amt = p.get("amount") or p.get("value") or 1
        unit = ((p.get("measureUnit") or {}).get("name") or "").strip()
        mod = (p.get("modifier") or "").strip()
        if mod.isdigit():                      # FNDDS portion codes (90000 = typical amount), not words
            return "1 serving" if mod == "90000" else "1 portion"
        amt = int(amt) if float(amt).is_integer() else round(float(amt), 2)
        unit = "" if unit.lower() in ("undetermined", "") else unit
        label = " ".join(x for x in (str(amt), unit, mod) if x).strip()
    # tidy USDA bookkeeping out of the label
    label = re.sub(r"\s*\((yield|NLEA)[^)]*\)?", "", label, flags=re.I)
    label = re.sub(r"\s*,?\s*(excluding refuse|yield from).*$", "", label, flags=re.I)
    label = re.sub(r"\s*From \d+.*$", "", label)
    label = re.sub(r"\s*\b[\w']+ label \d{4}$|\s*label \d{4}$|\s*\d{4} label$", "", label, flags=re.I)
    label = re.sub(r"\bRACC\b", "serving", label)
    label = re.sub(r"\s+", " ", label).strip(" ,")
    if re.fullmatch(r"[\d./ ]*", label):
        return ""
    return label[:48]


def convert(food, source):
    cat = (food.get("foodCategory") or {}).get("description") or \
          (food.get("wweiaFoodCategory") or {}).get("wweiaFoodCategoryDescription") or ""
    if cat in SKIP_CATEGORIES or "baby" in cat.lower() or "infant" in cat.lower():
        return None
    n = {}
    energy_alt = None
    for fn in food.get("foodNutrients") or []:
        num = str((fn.get("nutrient") or {}).get("number") or "")
        amt = fn.get("amount")
        if amt is None:
            continue
        if num in NUTR:
            n[NUTR[num]] = amt
        elif num in ENERGY_FALLBACK and energy_alt is None:
            energy_alt = amt
    if "cal" not in n and energy_alt is not None:
        n["cal"] = energy_alt
    if "cal" not in n:
        return None
    brand, name = tidy((food.get("description") or "").strip())
    portions = []
    for p in food.get("foodPortions") or []:
        g = p.get("gramWeight")
        lab = portion_label(p)
        if g and lab and len(portions) < 4 and all((lab, round(float(g))) != (x[0], round(x[1])) for x in portions):
            portions.append([lab[:60], round(float(g), 1)])
    rec = {"id": food.get("fdcId"), "n": name, "src": source,
           "k": {key: (round(v) if key in ("cal", "sod") else round(v, 1)) for key, v in n.items()},
           "u": portions}
    if brand:
        rec["b"] = brand
    if cat:
        rec["cat"] = cat
    if brand or cat.lower() in ("fast foods", "restaurant foods"):
        rec["r"] = 1  # restaurant / fast food
    return rec


def main():
    urls = latest_urls()
    groups, total = {}, 0
    for source in ("foundation", "sr", "survey"):
        foods = load_foods(urls[source])
        kept = 0
        for f in foods:
            rec = convert(f, {"foundation": "F", "sr": "S", "survey": "V"}[source])
            if not rec:
                continue
            total += 1
            cleaned = food_names.clean(rec["n"], rec.get("b"))
            if not cleaned:
                continue
            brand, disp, info = cleaned
            # FNDDS describes food "as eaten": its beans and grains are cooked even when unlabelled
            if source == "survey" and info["grain"] and not info["dry"] and not info["method"] \
                    and not re.search(r"\b(fried|salad|soup|pudding)\b", disp, re.I):
                info["method"] = True
                disp += ", cooked"
            rec.update(n=disp, _info=info, _orig=f.get("description") or "")
            if brand:
                rec["b"], rec["r"] = brand, 1
            key = food_names.dedup_key(brand, disp)
            groups[key] = food_names.pick_better(groups[key], rec) if key in groups else rec
            kept += 1
        print(f"  {source}: {kept} of {len(foods)}")
    out = []
    for rec in groups.values():
        info = rec.pop("_info"); rec.pop("_orig", None)
        out.append(rec)
    print(f"{total} USDA foods -> {len(out)} after cleaning names and removing cooking-style duplicates")
    if len(out) < 1000:
        print("Too few foods came back; keeping the previous file.", file=sys.stderr)
        sys.exit(1)
    payload = {"source": "USDA FoodData Central (public domain, CC0) - fdc.nal.usda.gov",
               "built": time.strftime("%Y-%m-%d"), "files": {k: v.rsplit("/", 1)[-1] for k, v in urls.items()},
               "count": len(out), "foods": out}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {OUT}: {len(out)} foods, {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
