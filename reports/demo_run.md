# Sorted demo run (synthetic simulation)

`make demo` replays 6 simulated months of synthetic bills in seconds to show how the share of local code grows; no real user data or history. Dates are generated so the simulated timeline ends on the run date (14 Oct 2026); the simulation lives in `data/demo.db`, separate from the live bot's database.

LLM routes: small=cerebras/gpt-oss-120b, strong=openai/gpt-5.4. Compile after 3 accepted traces; shadow runs = 1 (demo setting; default 2). Costs are estimates from BRAIN_PRICES.

```text
Generated 76 synthetic messages (emails, SMS, PDFs) for Sim months 1-6.

=== Sim month 1 of 6 (synthetic) ===
  15 Apr email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 04 May [open]
  15 Apr sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 04 May            [duplicate]
  17 Apr sms   HDFCBK                   -                                                                           [OTP dropped before storage]
  19 Apr email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 19 May             [open]
  19 Apr email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹959.00 due 04 May       [open]
  23 Apr email myntra.com               LLM       ignore                                                            [ignored]
  24 Apr email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 12 May               [open]
  24 Apr email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 29 Apr              [open]
  26 Apr email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹25,264.52 due 16 May        [open]
  26 Apr sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹25,264.52 due 16 May        [duplicate]
  02 May email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 01 Jun             [open]
  ⏰ 28 Apr 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 29 Apr.
  ⏰ 01 May 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 04 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 01 May 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹959.00 is due on 04 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 May 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 12 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 13 May 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹25,264.52 is due on 16 May. Reply 'paid' when done, or 'snooze 1h'.
  [ml] retrained the local classifier on 10 LLM-labelled messages (0 sender rules)
  -- 10 messages, 0 handled by local code, 10 LLM calls, privacy score 0%

=== Sim month 2 of 6 (synthetic) ===
  15 May email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 03 Jun [open]
  15 May sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 03 Jun            [duplicate]
  16 May sms   JIOMRT                   LLM       ignore                                                            [ignored]
  19 May email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 19 Jun             [open]
  19 May email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹2,051.00 due 03 Jun     [open]
  24 May email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 11 Jun               [open]
  25 May email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 30 May              [open]
  25 May pdf   pdf                      LLM       document_expiry            Transport Department  due 24 Nov       [document]
  26 May email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹15,425.79 due 15 Jun        [open]
  26 May sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹15,425.79 due 15 Jun        [duplicate]
  31 May sms   AMAZON                   -                                                                           [OTP dropped before storage]
  01 Jun email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 02 Jul             [open]
  05 Jun email swiggy.in                LLM       ignore                                                            [ignored]
  ⏰ 29 May 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 30 May.
  ⏰ 31 May 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 03 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 31 May 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹2,051.00 is due on 03 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 08 Jun 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 11 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 12 Jun 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹15,425.79 is due on 15 Jun. Reply 'paid' when done, or 'snooze 1h'.
  [ml] retrained the local classifier on 22 LLM-labelled messages (9 sender rules)
  -- 12 messages, 0 handled by local code, 12 LLM calls, privacy score 0%

=== Sim month 3 of 6 (synthetic) ===
  15 Jun email airtel.com               LLM       bill_due                   Airtel ₹1,178.82 due 04 Jul            [open]
  15 Jun sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 04 Jul            [duplicate]
  16 Jun pdf   pdf                      LLM       document_expiry            ICICI Lombard  due 03 Nov              [document]
  19 Jun email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 19 Jul             [open]
  19 Jun email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹3,559.00 due 04 Jul     [open]
  22 Jun email spotify.com              LLM       subscription_price_change  Spotify ₹139.00 due 19 Jul             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Spotify is raising your price from ₹119 to ₹139 on 19 Jul 2026. Reply KEEP or CANCEL-HELP.
  24 Jun email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 12 Jul               [open]
  25 Jun email secure-payments-update.c RULE      ignore                                                            [ignored]
  26 Jun email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹27,884.72 due 16 Jul        [open]
  26 Jun sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹27,884.72 due 16 Jul        [duplicate]
  26 Jun email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 01 Jul              [open]
  28 Jun sms   AIRTEL                   LLM       ignore                                                            [ignored]
  02 Jul email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 01 Aug             [open]
  04 Jul email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 03 Nov    [open]
  ⏰ 30 Jun 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 01 Jul.
  ⏰ 01 Jul 09:00 reminder fired by the scheduler (no LLM): Airtel bill ₹1,178.82 is due on 04 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 01 Jul 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹3,559.00 is due on 04 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 Jul 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 12 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 13 Jul 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹27,884.72 is due on 16 Jul. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] airtel_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1054 tokens)
  [approval] auto-approved for demo: airtel_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_airtel_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 963 tokens)
  [approval] auto-approved for demo: sms_airtel_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] spotify_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 996 tokens)
  [approval] auto-approved for demo: spotify_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] bsesdelhi_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1075 tokens)
  [approval] auto-approved for demo: bsesdelhi_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] licindia_in_premium_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1074 tokens)
  [approval] auto-approved for demo: licindia_in_premium_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] apolloclinic_com_meeting v1: candidate (2 visible + 1 held-out cases, held-out pass 0%, 3555 tokens) — example 1: expected {"type": "meeting", "provider": "Apollo Clinic", "currency": "INR", "due_date": "2026-05-30", "event_time": "10:30", "person": "Sunita Sharm
  [compiler] hdfcbank_net_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1167 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_hdfcbk_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 973 tokens)
  [approval] auto-approved for demo: sms_hdfcbk_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] account_netflix_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1001 tokens)
  [approval] auto-approved for demo: account_netflix_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 35 LLM-labelled messages (10 sender rules)
  -- 14 messages, 1 handled by local code, 22 LLM calls, privacy score 7%

=== Sim month 4 of 6 (synthetic) ===
  15 Jul email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,414.82 due 03 Aug [open]
      ↳ ability:airtel_com_bill_due@v1 shadow match 1/1 -> active
  15 Jul sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,414.82 due 03 Aug            [duplicate]
      ↳ ability:sms_airtel_bill_due@v1 shadow match 1/1 -> active
  19 Jul email spotify.com              LLM       subscription_receipt       Spotify ₹139.00 due 19 Aug             [open]
      ↳ ability:spotify_com_subscription_receipt@v1 shadow match 1/1 -> active
  19 Jul email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹1,596.00 due 03 Aug     [open]
      ↳ ability:bsesdelhi_com_bill_due@v1 shadow match 1/1 -> active
  23 Jul sms   SBIINB                   -                                                                           [OTP dropped before storage]
  24 Jul email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 11 Aug               [open]
      ↳ ability:licindia_in_premium_due@v1 shadow match 1/1 -> active
  24 Jul email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 29 Jul              [open]
  26 Jul email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹32,088.85 due 15 Aug        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 shadow match 1/1 -> active
  26 Jul sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹32,088.85 due 15 Aug        [duplicate]
      ↳ ability:sms_hdfcbk_bill_due@v1 shadow match 1/1 -> active
  01 Aug email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 01 Sep             [open]
      ↳ ability:account_netflix_com_subscription_receipt@v1 shadow match 1/1 -> active
  03 Aug email account.netflix.com      LLM       subscription_price_change  Netflix ₹649.00 due 01 Sep             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Netflix is raising your price from ₹499 to ₹649 on 01 Sep 2026. Reply KEEP or CANCEL-HELP.
  04 Aug email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 03 Nov    [duplicate]
  14 Aug email amazon.in                LLM       ignore                                                            [ignored]
      ↳ local classifier unsure (ignore 0.47 < 0.7) -> LLM
  ⏰ 17 Jul 09:00 reminder fired by the scheduler (no LLM): Spotify price rises to ₹139 on 19 Jul 2026. Keep it or cancel before then.
  ⏰ 28 Jul 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 29 Jul.
  ⏰ 31 Jul 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,414.82 is due on 03 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 31 Jul 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹1,596.00 is due on 03 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 08 Aug 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 11 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 12 Aug 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹32,088.85 is due on 15 Aug. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] apolloclinic_com_meeting v1: tested (3 visible + 1 held-out cases, held-out pass 100%, 2052 tokens)
  [approval] auto-approved for demo: apolloclinic_com_meeting v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 47 LLM-labelled messages (11 sender rules)
  -- 12 messages, 0 handled by local code, 13 LLM calls, privacy score 0%

=== Sim month 5 of 6 (synthetic) ===
  15 Aug email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 03 Sep [open]
      ↳ local code
  15 Aug sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 03 Sep            [duplicate]
      ↳ local code
  17 Aug email hdfcbank.net             LLM       ignore                                                            [ignored]
  19 Aug email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 19 Sep             [open]
      ↳ local code
  19 Aug email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹965.50 due 03 Sep       [open]
      ↳ local code
  24 Aug email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 11 Sep               [open]
      ↳ local code
  25 Aug email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 30 Aug              [open]
      ↳ ability:apolloclinic_com_meeting@v1 shadow match 1/1 -> active
  26 Aug email hdfcbank.net             LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 15 Sep        [open]
      ↳ local code
  26 Aug sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 15 Sep        [duplicate]
      ↳ local code
  01 Sep email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 02 Oct             [open]
      ↳ local code
  04 Sep email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 03 Nov    [duplicate]
  08 Sep sms   ICICIP                   LLM       ignore                                                            [ignored]
  ⏰ 29 Aug 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 30 Aug.
  ⏰ 30 Aug 09:00 reminder fired by the scheduler (no LLM): Netflix price rises to ₹649 on 01 Sep 2026. Keep it or cancel before then.
  ⏰ 31 Aug 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 03 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 31 Aug 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹965.50 is due on 03 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 08 Sep 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 11 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 12 Sep 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹19,391.89 is due on 15 Sep. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] icicilombard_com_insurance_renewal v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1091 tokens)
  [approval] auto-approved for demo: icicilombard_com_insurance_renewal v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 51 LLM-labelled messages (11 sender rules)
  -- 12 messages, 8 handled by local code, 5 LLM calls, privacy score 67%

=== Sim month 6 of 6 (synthetic) ===
  15 Sep email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 04 Oct [open]
      ↳ local code
  15 Sep sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 04 Oct            [duplicate]
      ↳ local code
  15 Sep sms   AIRTEL                   -                                                                           [OTP dropped before storage]
  16 Sep email youtube.com              LLM       subscription_price_change  YouTube ₹149.00 due 26 Oct             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: YouTube is raising your price from ₹129 to ₹149 on 26 Oct 2026. Reply KEEP or CANCEL-HELP.
  19 Sep email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 19 Oct             [open]
      ↳ local code
  19 Sep email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹1,758.50 due 04 Oct     [open]
      ↳ local code
  21 Sep pdf   pdf                      LLM       bill_due                   BSES Rajdhani ₹1,758.50 due 04 Oct     [duplicate]
  24 Sep email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 12 Oct               [open]
      ↳ local code
  26 Sep email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹13,903.23 due 16 Oct        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 failed (ValueError: Missing Payment Due Date label) -> degraded, LLM fallback
  26 Sep sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹13,903.23 due 16 Oct        [duplicate]
      ↳ local code
  26 Sep email apolloclinic.com         LOCAL v1  meeting                    Apollo Clinic  due 01 Oct              [open]
      ↳ local code
  27 Sep email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 03 Nov    [duplicate]
      ↳ ability:icicilombard_com_insurance_renewal@v1 shadow match 1/1 -> active
  02 Oct email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 01 Nov             [open]
      ↳ local code
  ⏰ 30 Sep 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 01 Oct.
  ⏰ 01 Oct 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 04 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 01 Oct 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹1,758.50 is due on 04 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 Oct 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 12 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 13 Oct 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹13,903.23 is due on 16 Oct. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] hdfcbank_net_bill_due v2: tested (3 visible + 2 held-out cases, held-out pass 100%, 1533 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v2 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 55 LLM-labelled messages (11 sender rules)
  -- 12 messages, 8 handled by local code, 5 LLM calls, privacy score 67%
```

## Abilities

| ability | version | status | runs | failures | last error |
|---|---|---|---|---|---|
| account_netflix_com_subscription_receipt | v1 | active | 3 | 0 |  |
| airtel_com_bill_due | v1 | active | 3 | 0 |  |
| apolloclinic_com_meeting | v1 | active | 2 | 0 |  |
| bsesdelhi_com_bill_due | v1 | active | 3 | 0 |  |
| hdfcbank_net_bill_due | v1 | degraded | 3 | 1 | ValueError: Missing Payment Due Date label |
| hdfcbank_net_bill_due | v2 | shadow | 0 | 0 |  |
| icicilombard_com_insurance_renewal | v1 | active | 1 | 0 |  |
| licindia_in_premium_due | v1 | active | 3 | 0 |  |
| sms_airtel_bill_due | v1 | active | 3 | 0 |  |
| sms_hdfcbk_bill_due | v1 | active | 3 | 0 |  |
| spotify_com_subscription_receipt | v1 | active | 3 | 0 |  |

Generated code and its tests: `abilities/<name>/v<n>/` (run them with `uv run pytest abilities`).

## Reminders still scheduled after the simulation (all in the future; fire with no LLM)

- 24 Oct 2026 09:00 — YouTube price rises to ₹149 on 26 Oct 2026. Keep it or cancel before then.
- 27 Oct 2026 09:00 — ICICI Lombard renewal ₹14,860.00 is due on 03 Nov. Reply 'paid' when done, or 'snooze 1h'.

## TinyFish (web)

Agent API run (replayed from tests/fixtures/tinyfish/) on https://help.netflix.com/en/node/24926: `{'provider': 'Netflix', 'plan': 'Standard', 'price': 19.99, 'currency': 'USD'}`, stored as a `portal` trace so the task can graduate like any other. (TinyFish proxies have no India exit, so the public page shows US pricing.)

## Privacy score and cost per simulated month

| period | messages | local code | LLM calls | tokens | privacy score | cost / message (USD) |
|---|---|---|---|---|---|---|
| Sim month 1 | 10 | 0 | 10 | 9643 | 0% | 0.00043 |
| Sim month 2 | 12 | 0 | 12 | 11348 | 0% | 0.00042 |
| Sim month 3 | 14 | 1 | 22 | 25877 | 7% | 0.00605 |
| Sim month 4 | 12 | 0 | 13 | 13730 | 0% | 0.00169 |
| Sim month 5 | 12 | 8 | 5 | 5398 | 67% | 0.00075 |
| Sim month 6 | 12 | 8 | 5 | 5685 | 67% | 0.00105 |

## Extraction accuracy (`make eval`)

Labelled samples: 76 (`data/eval/labels.jsonl`)

| handler | type | provider | amount | due_date |
|---|---|---|---|---|
| all | 98.6% (71/72) | 100.0% (64/64) | 98.4% (63/64) | 100.0% (64/64) |
| llm | 98.2% (54/55) | 100.0% (48/48) | 97.9% (47/48) | 100.0% (48/48) |
| compiled | 100.0% (16/16) | 100.0% (16/16) | 100.0% (16/16) | 100.0% (16/16) |
| rule | 100.0% (1/1) | - | - | - |
| ability:account_netflix_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:airtel_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:apolloclinic_com_meeting@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:bsesdelhi_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:hdfcbank_net_bill_due@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:licindia_in_premium_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_airtel_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_hdfcbk_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:spotify_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| rule:injection_guard | 100.0% (1/1) | - | - | - |


## Chat (answers from the simulated state only)

> What do I need to pay in the next two weeks?

₹13,903.23 for HDFC Bank bill (due 16 Oct) and ₹139 for Spotify subscription (due 19 Oct).

LLM calls this run: 0 live, 69 replayed from `data/llm_cache/`.
