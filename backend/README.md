# Price submissions backend

Students report prices from the app. This Google Apps Script receives them, denies junk automatically, and keeps the rest for your approval in a Google Sheet. The daily data job then copies approved prices into `data/dining.json`.

## Set up (about 5 minutes)

1. Create a new Google Sheet named **HokieMacros prices**.
2. **Extensions → Apps Script.** Delete what's there, paste all of `Code.gs`, and save.
3. Pick **setup** in the function menu and click **Run**. Approve the permissions. This creates the Review, Auto-denied and Confirmations tabs plus the 8 PM daily email.
4. **Deploy → New deployment →** type **Web app**. Execute as **Me**, access **Anyone**. Deploy and copy the URL ending in `/exec`.
5. Put that URL in `index.html` as `const PRICE_API='…'`. The app and the data job both read it from there.

## Reviewing

Open the **Review** tab and change **Decision** from Pending to **Approve** or **Reject**. Approved prices reach the app the next time the data job runs (twice a day).

## What's denied automatically

Edit `RULES` at the top of `Code.gs` to change these.

- Over $30, or under $2 for 400+ calorie items, $1 for 200+ and $0.50 for anything else
- Outside 60%–160% of the approved price, or 50%–200% of other pending reports when there are 2+
- More than 20 reports from one phone in 24 hours, or 150 already waiting
- D2 and Owens (they use door prices), unknown items, names containing links

A report within 5 cents of the approved price is logged as a confirmation and never reaches you. A phone that reports the same item again replaces its earlier pending report.

If you change `Code.gs` later: **Deploy → Manage deployments → Edit → New version**, so the URL stays the same.
