# Grants.gov search2 (public)

## Endpoint

- **Production:** `POST https://api.grants.gov/v1/api/search2`
- **Staging:** `https://api.staging.grants.gov` (same path pattern)
- **Auth:** not required for `search2` or `fetchOpportunity`
- **Header:** `Content-Type: application/json`

## Minimal body

```json
{
  "keyword": "specialty crop",
  "oppStatuses": "posted",
  "rows": 10,
  "startRecordNum": 0
}
```

## Useful body fields

| Field | Notes |
|-------|--------|
| `keyword` | Free text |
| `oppStatuses` | e.g. `posted` or `forecasted\|posted` |
| `rows` | Page size (script caps at 25) |
| `startRecordNum` | Pagination offset |
| `agencies` | Agency filter when known |
| `fundingCategories` | Category codes when known |
| `aln` | Assistance Listing Number |
| `eligibilities` | Eligibility filter codes |

## Response shape (success)

- Top-level: `errorcode` (0 = ok), `msg`, `data`
- Hits: `data.oppHits[]` with fields commonly including:
  - `id`, `number`, `title`
  - `agencyCode`, `agencyName`
  - `openDate`, `closeDate`
  - `oppStatus`, `docType`
  - `alnist` (list of ALN strings)

## Opportunity URL

If no link on hit:

`https://www.grants.gov/search-results-detail/{id}`

## cURL smoke

```bash
curl -sS -X POST 'https://api.grants.gov/v1/api/search2' \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"honey bee","oppStatuses":"posted","rows":5}'
```

## Security

- Do not commit API keys for *other* Grants.gov S2S APIs.
- search2 is public; still use a clear User-Agent and modest rate.
- Always re-check close dates on the opportunity page before advising anyone.

## Source docs (scraped 2026-07-22)

- https://grants.gov/api/api-guide
- https://grants.gov/api/common/search2
