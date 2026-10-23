# 05: The synthetic dataset

One deterministic generator, `brain/samples.py`, writes the **only** dataset. Tests, `make demo`, `make sim` and
`make eval` all use it. It is committed in `data/samples/` with labels in `data/eval/labels.jsonl`.
`make dataset` (`python -m brain.samples [END_DATE]`) regenerates it so the timeline ends on `END_DATE`
(default: today). Everything is fake: names, card/account/policy numbers, phones, amounts. The RNG is
`random.Random(42)`, reset on every `generate()`.

## Timeline and date shifting

- **Canonical timeline:** 2026-04-01 … `CANON_END = 2026-09-30`. Canonical month `m` (4…9) is **Sim month
  `m − 3`** (1…6).
- **Shifting:** every date is `canonical + SHIFT`, where `SHIFT = END − CANON_END`. The committed copy uses
  END = 2026-10-23 (offset 23 days).
- **Manifest:** `data/samples/dataset.json` = `{"end": "2026-10-23", "offset_days": 23, "messages": 81, "note":
  "Synthetic: …"}`. `samples.dataset_end()` reads it, falling back to `CANON_END`.
- **Sample ids** start with `m<SimMonth>_` (SMS ids `sms_m<n>_`), which is how `sim_sample()` and `score` find
  the Sim month.
- **Why shift:** the demo's timeline must end "today", so nothing it schedules is in the past. Recorded LLM
  answers are stored with the offset they were recorded at, and their dates are moved on replay (02 §6).

## Persona

- **The household:** Rohan Sharma (the user, Delhi), his mother Sunita Sharma, son Aarav (Grade 4).
- **Recipient address:** `rohan.sharma.demo@example.in`. Times are IST.
- **Email construction:** `EmailMessage`, HTML bodies unless noted, `Message-ID: <id@samples.sorted.local>`.
- **Indian number formatting:** `inr(123456.5) == "1,23,456.50"`.

## Contents: 81 messages (59 email, 19 SMS, 3 PDF)

**Per Sim month:** 11 / 13 / 15 / 13 / 13 / 16 samples. The privacy table counts 10 / 12 / 15 / 12 / 13 / 15,
because the 4 OTP SMS are dropped before they become tasks.

**By label type:** bill_due 31, subscription_receipt 12, ignore 12, meeting 7, premium_due 6,
insurance_renewal 5, meeting_request 4, subscription_price_change 3, document_expiry 1.

### Recurring, every Sim month 1–6 (generated per canonical month m with index i = 0…5)

| id | Sender | Content | Label |
|---|---|---|---|
| `m{n}_hdfc_cc` | `HDFC Bank Credit Cards <emailstatements.cards@hdfcbank.net>` | Statement date the 12th; due = statement + 20 days; total = uniform(8000, 35000); minimum = max(200, 5%). **Sim months 1–5:** subject "Your HDFC Bank Credit Card Statement for {Month YYYY}", an HTML table with rows Card Number (XXXX XXXX XXXX 4821), Statement Date dd/mm/YYYY, Payment Due Date dd/mm/YYYY, Total Amount Due "Rs. 1,23,456.78", Minimum Amount Due. **Sim month 6 (the layout change):** subject "HDFC Bank Credit Card e-Statement \| Mon YYYY \| Card ending 4821", `div.kpi` blocks "Amount payable / INR …", "Pay by / dd Mon YYYY", "Min. payable"; no "Total Amount Due" label | bill_due, HDFC Bank, total, due; extras `minimum_due`, `layout` v1/v2 |
| `sms_m{n}_hdfc` | `VM-HDFCBK` | "HDFC Bank Credit Card XX4821 statement generated. Total due: Rs.{total:.2f}, Min due: Rs.{min:.2f}, Due date: {dd-Mon-yy}. Pay on time to avoid charges." The same fact as the email (a duplicate) | bill_due, HDFC Bank |
| `m{n}_bses` | `BSES Rajdhani Power Ltd <ebill@bsesdelhi.com>` | Bill the 5th, due the 20th; units randint(180, 620) in canonical May–Jul, else (120, 300); amount = units × 6.5 + 140; CA No. 151234567; table rows Bill Date dd.mm.YYYY, Units Consumed, Net Amount Payable (Rs.), Due Date | bill_due, BSES Rajdhani |
| `m{n}_airtel` | `Airtel Xstream Fiber <ebill@airtel.com>` | Bill the 1st, due the 20th; ₹1,178.82 (₹1,414.82 in canonical July); account 3000123456; plain lines "Amount due: ₹…", "Due date: dd-Mon-YYYY" | bill_due, Airtel |
| `sms_m{n}_airtel` | `AX-AIRTEL` | "Dear Customer, your Airtel Xstream bill of Rs {amount:.2f} for a/c 3000123456 is due on {dd-Mon-YYYY}. Pay now via Airtel Thanks app." | bill_due, Airtel |
| `m{n}_lic` | `LIC of India <noreply@licindia.in>` | **Plain text.** Sent the 10th, due the 28th; "PREMIUM DUE NOTICE"; Policy No 912345678; Jeevan Anand (Table 915); Monthly (ECS); Premium Amount : Rs. 4,215.00; Due Date : dd/mm/YYYY | premium_due, LIC, 4215 |
| `m{n}_netflix_receipt` | `Netflix <info@account.netflix.com>` | Charged the 18th; ₹499.00, or ₹649.00 from canonical 2026-08-18; plan Standard; UPI AutoPay; next billing date = the 18th of next month | subscription_receipt, Netflix, price, next billing; `service` Netflix |
| `m{n}_spotify_receipt` | `Spotify <no-reply@spotify.com>` | Charged the 5th; Rs 119, or Rs 139 from canonical 2026-07-05; random Order ID; "Your next payment of Rs X is on dd/mm/YYYY." | subscription_receipt, Spotify |
| `m{n}_apollo_appt` | `Apollo Clinic <appointments@apolloclinic.com>` | An appointment on the (15 + i % 3)th, sent 5 days earlier; for **Sunita Sharma** with Dr. Anjali Mehta (Endocrinology) at 10:30 AM; Sector 18, Noida; **an `invite.ics` attachment** (VEVENT 10:30–11:00) | meeting, Apollo Clinic, no amount, appt date; `event_time` "10:30", `person` Sunita Sharma |

### One-offs

| id | What |
|---|---|
| `m3_spotify_price` | Spotify Premium price change Rs 119 → Rs 139 from canonical 2026-07-05; sent canonical 2026-06-08 |
| `m4_netflix_price` | Netflix Standard ₹499 → ₹649 from canonical 2026-08-18; sent 2026-07-20 |
| `m6_youtube_price` | `YouTube <noreply-purchases@youtube.com>`: an **unseen sender**, ₹129 → ₹149 from canonical 2026-10-12; sent 2026-09-02; label service "YouTube Premium" |
| `m{3,4,5,6}_icici_car` | `ICICI Lombard <renewals@icicilombard.com>`: car policy 3001/CAR/12345678/00/000, vehicle DL 3C AB 1234 (Hyundai i20), expires canonical 2026-10-20, renewal premium ₹14,860; sent canonical 06-20, 07-21, 08-21, 09-13; "that's N days from today" → insurance_renewal (extras policy, vehicle) |
| `m1_myntra_promo`, `m2_swiggy_promo`, `m4_amazon_promo`, `m5_bank_newsletter` | Promotions/newsletters, each with "Unsubscribe" (the newsletter is from `news@hdfcbank.net`, the same bank, a different address) → ignore |
| `m3_injection` | `Accounts Desk <billing@secure-payments-update.co>`, "URGENT: action required on your account": a fake overdue bill with **hidden 1px white text** containing classic prompt-injection instructions (pretends to be a system message, asks to forward all mail to an outside address, mark bills paid, delete the audit log and reveal card numbers) plus a phishing link → ignore, `injection: true`. It must never reach the LLM |
| `sms_m{1,2,4,6}_otp{0..3}` | OTP SMS from VM-HDFCBK, AD-AMAZON, VK-SBIINB, JD-AIRTEL: a 6-digit code with "OTP"/"verification code" wording → ignore, `otp: true`. They must be dropped before storage |
| `sms_m2_promo0`, `sms_m3_promo1`, `sms_m5_promo2` | Promotional SMS from BZ-JIOMRT, AD-AIRTEL, VM-ICICIP → ignore |
| `m6_clove_appt` | `Clove Dental <appointments@clovedental.in>`: the user's own dental appointment, canonical 2026-10-03 11:00 AM, sent 09-26 → meeting, Clove Dental, `person` Rohan Sharma |

### Meeting requests (someone asks for the user's time; not yet confirmed)

Each email is HTML: "Would you have some time on **{Weekday, dd Month YYYY} at {hh:mm AM/PM}** to discuss
{detail}? It should take about an hour. … Let me know if that works, or suggest another time." It is sent at
11:20 on the given canonical day. The id is `m{n}_meeting_<first word of topic>`.

| Sent (canon) | From | Org | Topic | Proposed |
|---|---|---|---|---|
| 06-18 | `Ankit Verma <ankit.verma@sharmaassociates.in>` | Sharma Associates | flat lease renewal | 2026-06-26 16:00 |
| 08-01 | `Delhi Public School <ptm@dpsrkpuram.edu.in>` (person Mrs. Kavita Rao) | Delhi Public School | parent-teacher meeting | 2026-08-08 10:00 |
| 09-03 | `Neha Gupta <neha@guptaca.in>` | Gupta & Co. Chartered Accountants | advance tax review | 2026-09-09 18:30 |
| 09-25 | `Ravi Kumar <ravi.kumar@acmeinfra.in>` | Acme Infra | kitchen renovation site visit | 2026-10-06 11:00 |

Label: `meeting_request`, provider = org, due = the proposed date, `event_time`, `person`, `topic`.

### PDFs (`data/samples/pdf/*.pdf`, written with fpdf2, Helvetica 11, `creation_date` = the "received" time)

| id | Content | Label |
|---|---|---|
| `m6_bses_bill` | A duplicate copy of the Sim-month-6 BSES bill (same units and amount), uploaded canonical 09-07 | bill_due BSES Rajdhani |
| `m3_icici_car_policy` | Policy schedule: the period of insurance ends 2026-10-20; Total Premium (incl. GST) Rs 15,342.00 | insurance_renewal ICICI Lombard 15342, `document_type` insurance_policy |
| `m2_puc_certificate` | PUC certificate DL0010000123456 for DL 3C AB 1234; tested 2026-05-11, **valid up to 2026-11-10** | document_expiry, Delhi Transport Department, `document_type` puc |

## Files

- `data/samples/email/<id>.eml`.
- `data/samples/sms/sms.jsonl`: one `{"id", "sender", "received_at" (ISO with +05:30), "body"}` per line,
  sorted by time.
- `data/samples/pdf/<id>.pdf`, `data/samples/dataset.json`.
- `data/eval/labels.jsonl`: one line per sample, sorted by id:
  ```json
  {"id": "m1_airtel", "kind": "email", "sender": "Airtel Xstream Fiber <ebill@airtel.com>", "type": "bill_due",
   "provider": "Airtel", "amount": 1178.82, "due_date": "2026-05-13"}
  ```
  The base keys are `id, kind, sender, type, provider, amount (2 dp or null), due_date (ISO or null)`. Extra keys
  are any of `minimum_due, layout, service, old_price, new_price, policy, vehicle, event_time, person, topic,
  document_type, otp, injection`.

## What the dataset is designed to show

- **Repeat senders:** 9 repeat sender/type groups (HDFC email + SMS, BSES, Airtel email + SMS, LIC, Netflix,
  Spotify, Apollo), with the 3rd example arriving in Sim month 3. The month-3 compile produces parsers; month 4 is
  shadow; month 5 is mostly local.
- **The layout change:** HDFC's in Sim month 6 → v1 fails "Missing Total Amount Due" → LLM fallback → v2.
- **Price rises:** Spotify, Netflix, and an unseen sender (YouTube) → the rule fires 3 alerts.
- **Duplicates across channels:** email + SMS of the same bill; a PDF copy of a bill.
- **Conflict-free amounts,** so duplicates are detected.
- **Apollo Clinic:** its varying day and the `.ics` make the parser harder. It failed its tests in Sim months
  3–5 and passed in month 6 in the recorded run.
- **Safety cases:** OTPs (dropped), injection (blocked), promos (the classifier learns `ignore`).
- **Meeting requests** for the booking flow, and a PUC certificate for document expiry.
