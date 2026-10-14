# Extraction eval

Labelled samples: 76 (`data/eval/labels.jsonl`)

| handler | type | provider | amount | due_date |
|---|---|---|---|---|
| all | 100.0% (72/72) | 96.9% (62/64) | 100.0% (64/64) | 100.0% (64/64) |
| llm | 100.0% (55/55) | 95.8% (46/48) | 100.0% (48/48) | 100.0% (48/48) |
| compiled | 100.0% (16/16) | 100.0% (16/16) | 100.0% (16/16) | 100.0% (16/16) |
| rule | 100.0% (1/1) | - | - | - |
| ability:account_netflix_com_subscription_receipt@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:airtel_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:apolloclinic_com_meeting@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:bsesdelhi_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:hdfcbank_net_bill_due@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:licindia_in_premium_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_airtel_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_hdfcbk_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:spotify_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| rule:injection_guard | 100.0% (1/1) | - | - | - |

## Dataset

| kind/type | n |
|---|---|
| email/bill_due | 18 |
| email/ignore | 5 |
| email/insurance_renewal | 4 |
| email/meeting | 6 |
| email/premium_due | 6 |
| email/subscription_price_change | 3 |
| email/subscription_receipt | 12 |
| pdf/bill_due | 1 |
| pdf/document_expiry | 1 |
| pdf/insurance_renewal | 1 |
| sms/bill_due | 12 |
| sms/ignore | 7 |

## Local classifier (scikit-learn, held-out)

5 stratified 70/30 splits of the labelled non-OTP samples (22 unseen per split).

| metric | mean over splits |
|---|---|
| accuracy (all predictions) | 90.0% |
| share with confidence >= 0.7 (decided locally if `ignore`) | 83.6% |
| accuracy of those confident predictions | 100.0% |

