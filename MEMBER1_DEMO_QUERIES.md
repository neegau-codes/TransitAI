# MEMBER1_DEMO_QUERIES.md

## Canonical Demo Queries

These four queries have been **tested** and are the only approved demo queries for the Expo presentation.

---

### 1. Aluva → Thrissur @ 08:00
**Request** (traditional API call):
```json
POST /api/search
{
  "source": "Aluva",
  "destination": "Thrissur",
  "departure_time": "08:00"
}
```
**Expected behavior**
- Returns a successful route response (`200 OK`).
- `origin` field in the response equals **Aluva**.
- `destination` field equals **Thrissur**.
- `departure_time` echoed as `08:00`.
- Normalized routes (`fastest`, `cheapest`, `fewest_transfers`) are present.
- All transit legs are labeled **SCHEDULED** and their `source` is **STATIC_SCHEDULE**.

---

### 2. "aluva ninn kaloor pokanam"
**Request** (AI/NLP endpoint):
```json
POST /api/ai-search
{
  "query": "aluva ninn kaloor pokanam"
}
```
**Expected behavior**
- Successful AI‑driven search (`200 OK`).
- NLP parser extracts:
  - `origin = "Aluva"`
  - `destination = "Kaloor"`
- Normalized routes are returned under the same schema as the regular `/api/search` endpoint.

---

### 3. "reach thrissur before 5 pm"
**Request** (AI/NLP endpoint):
```json
POST /api/ai-search
{
  "query": "reach thrissur before 5 pm"
}
```
**Expected behavior**
- AI parser extracts:
  - `arrival_deadline = "17:00"` (5 pm converted to 24‑hour format).
- **Origin is missing**; the backend **does not guess** an origin. Instead it returns an error with a clear validation message asking for the missing origin (status `422`).
- This is an intentional *validation/clarification* case, not a failure of the system.

---

### 4. "ernakulam to palakkad under 100 rs"
**Request** (AI/NLP endpoint):
```json
POST /api/ai-search
{
  "query": "ernakulam to palakkad under 100 rs"
}
```
**Expected behavior**
- Successful AI‑driven search (`200 OK`).
- NLP parser extracts:
  - `origin = "Ernakulam"`
  - `destination = "Palakkad"`
  - `budget_limit = 100` (interpreted as INR).
- Returned candidate routes respect the budget constraint (all fares ≤ 100 INR) based on the pre‑loaded demo dataset.
- Fare information remains **SCHEDULED** (static schedule based), never marked as real‑time.

---

## Data Truthfulness
- **Scheduled transit data** → `status: SCHEDULED`, `source: STATIC_SCHEDULE`
- **Walking / calculated values** → `status: ESTIMATED`, `source: CALCULATED_ESTIMATE`
- **Realtime telemetry** → `UNAVAILABLE` (explicitly reported by `/api/live`)
- No fake LIVE data is used; the API never pretends to have real‑time vehicle positions.
