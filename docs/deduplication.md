# Deduplication

The workflow avoids duplicate tickets for repeated observations of the same
GuardDuty finding by using a **stable deduplication key** derived from the
GuardDuty finding id.

## 1. Why deduplicate

GuardDuty emits the same finding multiple times as it is updated (new evidence,
new last-seen time, increased severity). Without deduplication each occurrence
would create a new ticket and flood the SOC queue.

## 2. Deduplication key generation

The key is the first 16 hex characters of the SHA-256 hash of the GuardDuty
finding id, prefixed with `gd-`:

```text
dedup_key = "gd-" + sha256(finding_id)[:16]
```

Implementation: `src/incident_response/jira.py::deduplication_key`.

Example:

```python
from incident_response.jira import deduplication_key
from incident_response.normalizer import normalize_event
import json

event = json.load(open("examples/guardduty-high-severity.json", encoding="utf-8"))
finding = normalize_event(event)
print(deduplication_key(finding))  # e.g. gd-24257196fd7ee4a3
```

## 3. Where the key is stored

The deduplication key is stored as a Jira **label** on the issue. When a
dedicated custom field is configured (`JiraConfig.finding_id_custom_field`), the
raw GuardDuty finding id is also written to that field for direct correlation.

## 4. Search before create (JQL)

Before creating a ticket, the workflow searches for an existing issue:

```sql
project = SEC AND labels = "gd-24257196fd7ee4a3"
```

When a custom field is configured:

```sql
project = SEC AND "customfield_10001" = "<finding id>"
```

Implementation: `src/incident_response/jira.py::build_jql_for_finding`.

## 5. Duplicate behavior

When a duplicate finding arrives (an issue with the same dedup key already
exists), the workflow:

1. Does **not** create another ticket.
2. Adds a **recurrence comment** (see `jira-ticket-schema.md`).
3. Updates **last-seen** time.
4. Updates **severity/priority if it increased**.
5. Increments and records the **occurrence count** and latest evidence.

## 6. Limitations

- Jira label search requires exact label equality; the key is deterministic so
  this is reliable, but labels are case-insensitive and limited to 255 chars
  (the 16-hex key is well within limits).
- If an operator manually removes the dedup label, a duplicate ticket may be
  created on the next occurrence.
- JQL `text ~` searches are not exact; the label-based correlation is preferred
  over free-text matching of the finding id.
- Cross-project correlation is not supported by the default JQL (it scopes to a
  single project key).
