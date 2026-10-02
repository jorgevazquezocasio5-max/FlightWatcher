"""
MCO -> SJU one-way price watcher (runs once per invocation; scheduled by GitHub Actions)
Dec 8, 2026 | 2 adults + 2 children (ages 3 and 7) | departures 10:00-19:00 | alert at <= $80 per passenger

Secrets (env vars): TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, ALERT_TO
  TWILIO_FROM = "+1XXXXXXXXXX" for SMS, or "whatsapp:+14155238886" for WhatsApp sandbox
Optional env: PRICES_ARE_TOTAL=1 if Google's listed price turns out to be for all 4 seats.
"""
import base64, csv, os, sys, urllib.parse, urllib.request
from datetime import date, datetime, time as dtime
from pathlib import Path

from fast_flights import FlightQuery, Passengers, create_query, get_flights

ORIGIN, DEST, DATE = "MCO", "SJU", "2026-12-08"
ADULTS, CHILDREN = 2, 2                     # kids 3 and 7 each need their own seat
PAX = ADULTS + CHILDREN
WINDOW = (dtime(10, 0), dtime(19, 0))      # earliest / latest departure
MAX_PER_PERSON = 80                         # USD per passenger
PRICES_ARE_TOTAL = os.environ.get("PRICES_ARE_TOTAL") == "1"

DATA = Path("data")
DATA.mkdir(exist_ok=True)
LOG = DATA / "flight_prices.csv"
STATE = DATA / "last_alert.txt"             # last alerted per-person price (no repeat texts)


def build_query():
    return create_query(
        flights=[FlightQuery(
            date=DATE, from_airport=ORIGIN, to_airport=DEST,
            earliest_departure_hour=WINDOW[0].hour,
            latest_departure_hour=WINDOW[1].hour,
        )],
        seat="economy", trip="one-way",
        passengers=Passengers(adults=ADULTS, children=CHILDREN),
        currency="USD", language="en-US",
    )


def pick(results):
    """Keep itineraries departing inside WINDOW; return sorted (per_person, airlines, dep, arr, stops)."""
    keep = []
    for r in results:
        h, m = r.flights[0].departure.time
        if not (WINDOW[0] <= dtime(h, m) <= WINDOW[1]):
            continue
        per_person = round(r.price / PAX) if PRICES_ARE_TOTAL else r.price
        ah, am = r.flights[-1].arrival.time
        keep.append((per_person, "/".join(r.airlines), f"{h:02d}:{m:02d}",
                     f"{ah:02d}:{am:02d}", len(r.flights) - 1))
    return sorted(keep)


def notify(msg):
    print(msg)
    sid, token = os.environ.get("TWILIO_SID"), os.environ.get("TWILIO_TOKEN")
    frm, to = os.environ.get("TWILIO_FROM"), os.environ.get("ALERT_TO")
    if not (sid and token and frm and to):
        print("Twilio env vars not set; skipping text.")
        return
    if frm.startswith("whatsapp:"):
        to = "whatsapp:" + to
    data = urllib.parse.urlencode({"From": frm, "To": to, "Body": msg}).encode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data)
    req.add_header("Authorization",
                   "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    urllib.request.urlopen(req)


def last_alert():
    try:
        return int(STATE.read_text())
    except Exception:
        return None


def main():
    if "--test" in sys.argv:
        notify("Flight bot test: alerts are working.")
        return 0
    if date.today() > date.fromisoformat(DATE):
        print("Travel date has passed; nothing to do.")
        return 0

    q = build_query()
    flights = pick(get_flights(q))          # raises on fetch/parse failure -> job fails -> GitHub emails you
    if not flights:
        print("No flights inside the time window (or Google returned nothing).")
        return 1

    best = flights[0]
    new_file = not LOG.exists()
    with LOG.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["checked_at_utc", "per_person_usd", "airlines", "dep", "arr", "stops"])
        w.writerow([datetime.utcnow().isoformat(timespec="minutes"), *best])

    print(f"Cheapest in window: ${best[0]}/person ({best[1]}, dep {best[2]}, stops {best[4]})")
    for f in flights[:5]:
        print("  ", f)

    prev = last_alert()
    if best[0] <= MAX_PER_PERSON and (prev is None or best[0] < prev):
        notify(f"MCO->SJU Dec 8: ${best[0]}/person (${best[0] * PAX} for {PAX}) "
               f"{best[1]} dep {best[2]}, {best[4]} stop(s). {q.url()}")
        STATE.write_text(str(best[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
