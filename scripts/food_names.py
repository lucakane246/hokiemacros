"""Turn USDA's catalogue names into names people would actually type, and collapse
cooking-style duplicates.

  "Bananas, raw"                                         -> "Banana"
  "Chicken, broilers or fryers, breast, meat only, raw"  -> "Chicken breast"
  "Oil, olive, salad or cooking"                         -> "Olive oil"
  "Yogurt, Greek, plain, nonfat"                         -> "Greek yogurt, plain, nonfat"
  "Beef, ground, 85% lean meat / 15% fat, raw"           -> "Ground beef, 85% lean / 15% fat"
  "Big Mac (McDonalds)"                                  -> brand McDonald's, "Big Mac"

Foods are listed raw/as-bought, without saying "raw". Cooking-style variants
(boiled, roasted, braised ...) of the same food are dropped. Exceptions:
  - grains, pasta and dried beans are listed dry (the default name) AND cooked
    ("White rice" and "White rice, cooked"), since cooked weight depends on how much
    water was absorbed
  - dishes where the method *is* the food stay: scrambled/fried/hard-boiled eggs,
    fried rice, mashed potatoes, french fries ...
"""
import re

def _full(words):
    return re.compile(r"^(?:" + "|".join(words) + r")$", re.I)

JUNK = _full([
    r"raw", r"fresh", r"unprepared", r"nfs", r"ns as to .*", r"all grades", r"choice", r"select", r"prime",
    r"imported", r"domestic", r"new zealand", r"australian", r"mixed species", r"mature seeds", r"immature seeds",
    r"broilers or fryers", r"meat only", r"variety meats and by-products", r"composite of .*", r"retail parts?",
    r"separable lean and fat", r"trimmed to .*", r"lip-on", r"with added solution", r"enriched", r"unenriched",
    r"commercially prepared", r"commercial", r"regular", r"year round average", r"upc.*", r"solids and liquids",
    r"drained solids", r"drained", r"drained and rinsed", r"with salt", r"without salt", r"no salt added",
    r"salt added", r"sodium added", r"ready-to-serve", r"ready-to-heat", r"unheated", r"heated", r"includes .*",
    r"from fast food / restaurant", r"fast food / restaurant", r"fast food", r"from restaurant", r"restaurant", r"edible portion", r"without bone",
    r"bone-in", r"boneless", r"dry heat", r"moist heat", r"no added fat", r"fat added", r"fat not added in cooking",
    r"skin not eaten", r"prepared from recipe", r"home recipe", r"home-prepared", r"as purchased",
    r"made with .* oil", r"made with butter", r"made with margarine", r"not further specified", r"all types",
    r"all varieties", r"all commercial varieties", r"with refuse", r"usda commodity", r"commodity", r"untrimmed",
    r"denuded", r"steak/roast", r"roast/steak", r"bnls", r"farmed", r"wild", r"raw or unheated", r"uncooked",
    r"with salt added", r"without added salt", r"with added salt", r"from raw", r"from pre-cooked", r"from precooked", r"unroasted", r"whole kernel", r"all forms", r"salad or cooking",
])
RENAME = [  # part -> nicer wording
    (r"^meat and skin$", "with skin"), (r"^skin eaten$", "with skin"), (r"^separable lean only$", "lean"),
    (r"^(\d+)% lean meat / (\d+)% fat$", r"\1% lean / \2% fat"), (r"^whole-wheat$", "whole wheat"),
]
METHOD = _full([
    r"cooked", r"boiled", r"roasted", r"baked", r"broiled", r"braised", r"steamed", r"microwaved", r"grilled",
    r"pan-fried", r"pan-broiled", r"pan-broil", r"stewed", r"simmered", r"toasted", r"blanched", r"heated in .*",
    r"baked or broiled", r"cooked in microwave", r"cooked, boiled", r"roasted, .*", r"braised, .*", r"rotisserie",
    r"oven-roasted", r"oven-heated", r"microwaved, .*", r"stir-fried", r"ns as to cooking method", r"fully cooked",
    r"cooked, .*", r"from frozen", r"from fresh", r"from canned", r"or (roasted|baked|broiled|grilled|fried|boiled)",
    r"(baked|broiled|roasted|grilled)( or (baked|broiled|roasted|grilled))+",
])
DISH_METHODS = re.compile(r"^(scrambled|fried|hard-boiled|hard-cooked|soft-boiled|poached|deviled|mashed|french fried|"
                          r"fried in .*|sunny side up|over easy|omelet|baked potato)$", re.I)
GRAIN_HEADS = {"rice", "pasta", "spaghetti", "macaroni", "noodles", "quinoa", "couscous", "barley", "bulgur",
               "beans", "lentils", "chickpeas", "peas", "farro", "millet", "buckwheat groats", "wild rice"}
DRY_WORDS = _full([r"dry", r"uncooked", r"dry form", r"dry, unenriched", r"raw"])

CATEGORY_HEADS = {"fish", "spices", "beverages", "snacks", "candies", "cereals ready-to-eat", "cereals",
                  "crustaceans", "mollusks", "game meat", "sweeteners", "alcoholic beverage", "condiments",
                  "leavening agents", "vegetables", "fruit", "fast foods", "restaurant", "luncheon meat", "nuts", "seeds"}
TYPE_HEADS = {"oil", "cheese", "juice", "sauce", "butter", "flour", "sugar", "bread", "milk", "yogurt", "rice",
              "beans", "pasta", "cereal", "soup", "tea", "coffee", "cream", "vinegar", "syrup",
              "jam", "jelly", "peppers", "squash", "lettuce", "cabbage", "onions", "mushrooms", "apples", "apple",
              "potatoes", "potato", "tomatoes", "tomato", "grapes", "melons", "salad dressing", "dressing",
              "crackers", "cookies", "cake", "pie", "muffin", "muffins", "rolls", "bagels", "tortillas", "chips",
              "pudding", "ice cream", "candy", "chocolate", "sausage", "bacon", "noodles", "lentils", "peas",
              "corn", "wine", "beer", "smoothie", "seasoning", "pepper", "salt", "mustard", "honey", "spread",
              "pizza", "stew", "pudding", "salad", "sandwich", "burrito", "taco", "chili", "curry", "casserole"}
MEAT_HEADS = {"chicken", "beef", "pork", "turkey", "lamb", "veal", "duck", "ham", "bison", "goat", "venison"}
CUTS = {"breast", "thigh", "wing", "wings", "drumstick", "leg", "ground", "tenderloin", "loin", "sirloin",
        "ribeye", "rib eye", "brisket", "chuck", "flank", "skirt", "ribs", "spareribs", "shoulder", "tenders",
        "liver", "gizzard", "heart", "neck", "back", "chop", "chops", "cutlet", "cutlets", "patty", "patties",
        "skin", "dark meat", "light meat", "white meat"}
FORM_WORDS = re.compile(r"^(canned|frozen|dried|powder|powdered|light|lite|reduced fat|low fat|lowfat|nonfat|fat free|"
                        r"fat-free|low sodium|reduced sodium|sweetened|unsweetened|instant|condensed|plain|flavored|"
                        r"with .*|without .*|and .*|or .*|in .*|prepared .*|ready-to-.*|\d.*|dry mix|mix|"
                        r"concentrate|frozen concentrate|diet|organic|reduced calorie|low calorie|mini|large|"
                        r"medium|small|jumbo|chopped|sliced|diced|shredded|grated|cubed|skin|flesh|flesh and skin|peel|leaves|"
                        r"stalks|kernels|.*\(.*)$", re.I)
SINGULAR = {"bananas": "banana", "apples": "apple", "oranges": "orange", "peaches": "peach", "pears": "pear",
            "plums": "plum", "apricots": "apricot", "eggs": "egg", "tomatoes": "tomato", "potatoes": "potato",
            "onions": "onion", "carrots": "carrot", "avocados": "avocado", "lemons": "lemon", "limes": "lime",
            "cucumbers": "cucumber", "mangos": "mango", "mangoes": "mango", "nectarines": "nectarine",
            "kiwifruit": "kiwi", "grapefruit": "grapefruit", "tangerines": "tangerine", "figs": "fig",
            "dates": "dates", "radishes": "radish", "turnips": "turnip", "beets": "beet", "parsnips": "parsnip",
            "shallots": "shallot", "leeks": "leek", "pickles": "pickle", "muffins": "muffin", "bagels": "bagel",
            "rolls": "roll", "tortillas": "tortilla", "puddings": "pudding", "sauces": "sauce", "waffles": "waffle", "pancakes": "pancake",
            "pretzels": "pretzels", "doughnuts": "doughnut", "croissants": "croissant", "biscuits": "biscuit"}
PROPER = {"greek", "italian", "french", "swiss", "american", "mexican", "thai", "chinese", "japanese", "indian",
          "cajun", "caesar", "alfredo", "parmesan", "cheddar", "mozzarella", "provolone", "brie", "gouda",
          "feta", "monterey", "colby", "ricotta", "romano", "asiago", "havarti", "muenster", "gruyere",
          "neufchatel", "atlantic", "pacific", "alaska", "alaskan", "california", "florida", "hawaiian",
          "english", "irish", "spanish", "turkish", "korean", "vietnamese", "cuban", "jamaican", "dijon",
          "worcestershire", "tabasco", "kalamata", "fuji", "gala", "granny", "smith", "honeycrisp",
          "red delicious", "golden delicious", "bartlett", "valencia", "navel", "concord", "thompson"}
FNDDS_BRANDS = {"mcdonalds": "McDonald's", "burger king": "Burger King", "wendys": "Wendy's", "taco bell": "Taco Bell",
                "subway": "Subway", "kfc": "KFC", "chick-fil-a": "Chick-fil-A", "starbucks": "Starbucks",
                "dunkin donuts": "Dunkin'", "dunkin": "Dunkin'", "pizza hut": "Pizza Hut", "dominos": "Domino's",
                "papa johns": "Papa John's", "sonic": "Sonic", "arbys": "Arby's", "dairy queen": "Dairy Queen",
                "popeyes": "Popeyes", "jack in the box": "Jack in the Box", "hardees": "Hardee's",
                "white castle": "White Castle", "little caesars": "Little Caesars", "chipotle": "Chipotle",
                "panera": "Panera", "five guys": "Five Guys", "krispy kreme": "Krispy Kreme"}


def _brand_from_paren(name):
    m = re.search(r"\s*\(([^()]+)\)\s*$", name)
    if not m:
        return None, name
    inner = m.group(1).strip()
    key = re.sub(r"['’.]", "", inner).lower()
    for k, nice in sorted(FNDDS_BRANDS.items(), key=lambda x: -len(x[0])):
        if key == k or key.startswith(k + " "):
            rest = inner[len(inner) - (len(key) - len(k)):].strip() if key != k else ""
            outer = name[:m.start()].strip()
            return nice, (rest or outer)
    return None, name


def _case(word, first):
    lw = word.lower()
    if lw in PROPER or re.sub(r"[^a-z]", "", lw) in PROPER:
        return word[:1].upper() + word[1:].lower()
    if not first and word[:1].isupper() and word[1:].islower() and len(word) > 1:
        return lw            # "Oil" moved behind "olive" -> "oil"
    return word


def clean(name, brand=None):
    """Return (brand, display_name, info) or None if the food should be dropped entirely.
    info: {"method": bool (a cooking-style variant), "dry": bool, "grain": bool, "base": head}"""
    if not brand:
        b, name = _brand_from_paren(name)
        brand = b or brand
    name = re.sub(r"\s*\((?:includes|formerly|nlea|upc)[^)]*\)", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name.replace(";", ",")).strip(" ,")
    parts = [p.strip() for p in name.split(",") if p.strip()]
    if not parts:
        return None
    head = parts[0]
    # category heads: "Fish, salmon, Atlantic" -> "Salmon, Atlantic"
    while head.lower() in CATEGORY_HEADS and len(parts) > 1 and not (METHOD.match(parts[1]) or JUNK.match(parts[1])):
        parts = parts[1:]
        head = parts[0]
    if parts[0] != name.split(",")[0].strip() and head.lower() in ("white", "mixed species", "other"):
        head = "white fish" if head.lower() == "white" else "fish"
    hl = head.lower()
    hl = SINGULAR.get(hl, hl)
    grain = hl in GRAIN_HEADS or any(g in hl for g in ("rice", "pasta", "spaghetti", "macaroni", "noodle"))
    method = dry = False
    quals = []
    for q in parts[1:]:
        ql = q.lower().strip()
        for pat, rep in RENAME:
            ql = re.sub(pat, rep, ql)
        if DISH_METHODS.match(ql):
            quals.append(ql)
            continue
        if METHOD.match(ql) or any(METHOD.match(x.strip()) for x in ql.split(" and ")):
            method = True
            continue
        if grain and DRY_WORDS.match(ql):
            dry = True
            continue
        if JUNK.match(ql):
            continue
        if JUNK.match(ql) or METHOD.match(ql):
            continue
        quals.append(re.sub(r"(?i)" + re.escape(q.strip()), ql, q.strip()) if ql != q.strip().lower() else q.strip())
    # drop duplicated words like "Pork, pork"
    if hl in MEAT_HEADS:
        quals = [q for q in quals if q.lower() != "whole"]
    quals = [" ".join(w.capitalize() if w.lower() in PROPER else w for w in q.split(" ")) for q in quals]
    quals = [q for i, q in enumerate(quals) if q.lower() != hl and q.lower() not in [x.lower() for x in quals[:i]]]

    # reorder for natural English
    head_words = SINGULAR.get(head.lower(), head)
    if head.lower() in SINGULAR:
        head_words = SINGULAR[head.lower()]
    elif head.lower() == hl:
        head_words = head
    moved = False
    if quals:
        q0 = quals[0]
        if hl == "egg" and q0.lower() == "whole":
            quals = quals[1:]
        elif hl == "egg" and q0.lower() in ("yolk", "white", "whites"):
            head_words, quals = f"Egg {q0.lower().rstrip('s')}", quals[1:]
        elif hl == "salad dressing" and len(q0.split()) <= 3:
            head_words, quals = f"{q0} dressing", quals[1:]
            moved = True
        elif hl in MEAT_HEADS and q0.lower() in CUTS:
            head_words = f"ground {hl}" if q0.lower() == "ground" else f"{head_words} {q0}"
            moved = True
            quals = quals[1:]
        elif hl in TYPE_HEADS and len(q0.split()) <= (3 if hl in ("soup", "stew", "pizza", "salad") else 2) and not FORM_WORDS.match(q0):
            head_words, quals = f"{q0} {head_words}", quals[1:]
            moved = True
    # moved-behind heads read lowercase ("olive Oil" -> "olive oil"); everything else keeps USDA's casing
    hw = head_words.split(" ")
    disp = " ".join(w.lower() if moved and i > 0 and w[:1].isupper() and w[1:].islower() and w.lower() not in PROPER
                    and w == hw[-1] else w for i, w in enumerate(hw))
    if quals:
        disp += ", " + ", ".join(quals[:3])
    disp = re.sub(r"\s+", " ", disp).strip(" ,")
    disp = disp[:1].upper() + disp[1:]
    if grain and method:
        disp += ", cooked"        # grains are listed dry by default; the cooked version is its own entry
    return brand, disp, {"method": method, "dry": dry, "grain": grain, "base": hl}


def pick_better(a, b):
    """Choose which of two foods with the same cleaned name to keep."""
    def score(r):
        info = r["_info"]
        s = 0
        s += 0 if info["method"] else 40          # raw / dry / as bought
        s += {"F": 6, "S": 4, "V": 2}.get(r["src"], 0)
        s -= len(r.get("_orig", "")) / 40
        s += 3 if r["u"] else 0
        s += 8 if re.search(r"(^|, )(raw|dry|uncooked)(,|$)", r.get("_orig", ""), re.I) else 0
        return s
    return a if score(a) >= score(b) else b


def dedup_key(brand, disp):
    words = re.sub(r"[^a-z0-9% ]+", " ", disp.lower()).split()
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words]
    return ((brand or "").lower(), " ".join(words))
