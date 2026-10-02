# MCO -> SJU flight watcher (GitHub Actions)

Checks Google Flights every 2 hours for a one-way MCO -> SJU flight on 2026-12-08,
2 adults + 2 children (ages 3 and 7), departing 10:00-19:00, and texts you when the cheapest fare is <= $80 per passenger
(only when it beats the last price it alerted on).

## Setup

1. **Create the repo.** On github.com: New repository -> name it `flight-watcher`.
   Public = unlimited free Actions minutes. Private also works (free tier gives 2,000 min/month;
   this uses roughly 100-150).
2. **Upload these files.** On the new repo page click "uploading an existing file" and drag in
   everything from the unzipped folder EXCEPT `SECRETS-CHECKLIST.txt`.
   The `.github` folder is hidden on your computer (Mac: Cmd+Shift+. in Finder; Windows: File Explorer >
   View > Show > Hidden items). If drag-and-drop skips it, do this instead:
   Add file > Create new file > type `.github/workflows/flight-watch.yml` as the name (the slashes
   create the folders), open the visible `flight-watch.yml` from the zip, copy everything, paste, Commit.
   Then you do not need to upload the loose `flight-watch.yml` copy.
3. **Twilio.** Create an account, then in the Console copy your Account SID and Auth Token.
   - WhatsApp (fastest): Messaging -> Try it out -> Send a WhatsApp message. Send the join code
     from your phone to the sandbox number. Sender = `whatsapp:+14155238886` (use the number
     shown in your console).
   - SMS: buy a US number. US carriers require sender registration before delivery is reliable;
     a trial account can text only numbers you've verified in Twilio.
4. **Add secrets.** Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
   | Name | Value |
   |---|---|
   | `TWILIO_SID` | your Account SID |
   | `TWILIO_TOKEN` | your Auth Token |
   | `TWILIO_FROM` | `whatsapp:+14155238886` or your Twilio SMS number (+1...) |
   | `ALERT_TO` | your phone in +1XXXXXXXXXX format |
5. **Test texting.** Actions tab -> "Flight watch" -> Run workflow -> tick `test` -> Run.
6. **Test the search.** Run workflow again with `test` unticked. Open the run log and check
   the printed cheapest fare against Google Flights.

## Things to verify on the first run

- **Per-person vs total price.** The bot assumes Google's listed price is per passenger.
  If the log shows roughly 4x what Google Flights displays per person, edit the workflow's
  "Check flights" step and add `PRICES_ARE_TOTAL: "1"` under `env:`.
- **Google blocking cloud IPs.** The bot reads Google Flights like a browser. Datacenter IPs
  are sometimes served a different page; if so the run fails and GitHub emails you.
  If that happens consistently, run it from a home machine/Raspberry Pi with cron instead.
- **Inactivity.** GitHub disables scheduled workflows after 60 days without repo activity.
  The bot commits `data/` whenever a check logs a row, which counts, and the trip date is
  only ~10 weeks away anyway.
- Always confirm the fare on the airline's site before booking.

Price history accumulates in `data/flight_prices.csv`.
