# Pincode dataset cross-check

Internal consistency sanity log on the embedded India Post pincode directory. **Not a gate** — anomalies are surfaced for manual review, not enforced. Fully offline, no external reference repo. See the header of `scripts/crosscheck_pincodes.py` for why we don't compare against captn3m0/india-pincode-regex.

## Totals

- Total pincodes: **26,711**
- Distinct 3-digit prefixes: **415**
- Distinct states: **39**
- Malformed pincode keys: **0**

## Prefix → state coherence

- Clean prefixes (single state): **371**
- Border prefixes (2 states): **40**
- Anomalous prefixes (3+ states): **4**

### Anomalous prefixes

| prefix | states |
|---|---|
| `396` | Dadra & Nagar Haveli, Daman & Diu, Gujarat |
| `495` | Chattisgarh, Chhattisgarh, Himachal Pradesh |
| `533` | Andhra Pradesh, Null, Pondicherry |
| `607` | Null, Pondicherry, Tamil Nadu |

### Border prefixes (sample, first 25)

| prefix | states |
|---|---|
| `160` | Chandigarh, Punjab |
| `244` | Uttar Pradesh, Uttarakhand |
| `246` | Uttar Pradesh, Uttarakhand |
| `247` | Uttar Pradesh, Uttarakhand |
| `249` | Uttar Pradesh, Uttarakhand |
| `262` | Uttar Pradesh, Uttarakhand |
| `362` | Daman & Diu, Gujarat |
| `465` | Chhattisgarh, Madhya Pradesh |
| `473` | Bihar, Madhya Pradesh |
| `486` | Chhattisgarh, Madhya Pradesh |
| `490` | Chattisgarh, Chhattisgarh |
| `491` | Chattisgarh, Chhattisgarh |
| `492` | Chattisgarh, Chhattisgarh |
| `493` | Chattisgarh, Chhattisgarh |
| `494` | Chattisgarh, Chhattisgarh |
| `496` | Chattisgarh, Chhattisgarh |
| `497` | Chattisgarh, Chhattisgarh |
| `500` | Andhra Pradesh, Telangana |
| `501` | Andhra Pradesh, Telangana |
| `502` | Andhra Pradesh, Telangana |
| `503` | Andhra Pradesh, Telangana |
| `504` | Andhra Pradesh, Telangana |
| `505` | Andhra Pradesh, Telangana |
| `506` | Andhra Pradesh, Telangana |
| `507` | Andhra Pradesh, Telangana |

## Top 10 states by pincode count

| state | pincodes |
|---|---|
| Tamil Nadu | 3,130 |
| Karnataka | 2,571 |
| Uttar Pradesh | 2,035 |
| Andhra Pradesh | 2,006 |
| Maharashtra | 1,929 |
| Kerala | 1,853 |
| Gujarat | 1,543 |
| West Bengal | 1,537 |
| Rajasthan | 1,464 |
| Bihar | 1,385 |

## Orphan states (<50 pincodes — possible spelling drift)

- Mizoram: 47
- Chattisgarh: 42
- Chandigarh: 30
- Sikkim: 28
- Pondicherry: 26
- Andaman Nicobar: 22
- Dadra & Nagar Haveli: 4
- Daman & Diu: 4
- Null: 4
- Lakshdweep: 1
- Andaman & Nicobar Islands: 1
