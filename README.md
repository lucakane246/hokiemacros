# HokieMacros

A free, ad-free nutrition tracker for Virginia Tech students on the meal plan.
Live menus, nutrition and hours for every dining hall, plus McComas and War Memorial gym hours, on a campus map.

## How the data stays current
`scripts/update_data.py` runs on GitHub Actions twice a day (about 4:17 AM and 10:47 AM Eastern).
It reads the same public feeds VT's own websites use:

| Data | Source |
|---|---|
| Menus + nutrition | foodpro.students.vt.edu (VT Dining Services) |
| Dining hours | apps.students.vt.edu/hours |
| McComas / War Memorial hours | apps.students.vt.edu/rshours (Rec Sports) |

and saves everything to `data/dining.json`, which the app loads. To refresh by hand, open the
**Actions** tab, pick **Update dining data**, and press **Run workflow**.

Map data © OpenStreetMap contributors.
Not affiliated with or endorsed by Virginia Tech.
