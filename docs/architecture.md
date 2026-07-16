# Architecture

This document contains the Mermaid diagrams for the system. All diagrams are
written to render correctly on GitHub.

## High-level architecture

```mermaid
flowchart LR
    GD["Amazon GuardDuty"] --> EB["Amazon EventBridge<br/>rule + severity filter"]
    EB -->|default: API Destination| TINES["Tines Webhook"]
    EB -->|optional: Lambda| LAMBDA["Lambda Forwarder<br/>(retries, masking)"]
    LAMBDA --> TINES
    TINES --> CORE["Validate • Normalize<br/>Severity map • Dedup key"]
    CORE --> JIRA["Jira Cloud REST API v3"]
    JIRA --> TICKET["Incident ticket<br/>(create / comment / transition)"]
    EB -.->|undeliverable| DLQ["SQS DLQ"]
    LAMBDA -.->|undeliverable| DLQ
    DLQ --> ALARM["CloudWatch alarms"]
    LAMBDA --> LOGS["CloudWatch Logs"]
```

## Event processing sequence

```mermaid
sequenceDiagram
    participant GD as GuardDuty
    participant EB as EventBridge
    participant T as Tines
    participant J as Jira
    GD->>EB: GuardDuty Finding event
    EB->>EB: pattern match + severity >= min
    alt API Destination
        EB->>T: POST finding (shared-secret header)
    else Lambda forwarder
        EB->>L: invoke
        L->>L: validate + normalize + mask
        L->>T: POST normalized payload (retries)
    end
    T->>T: verify auth + validate + normalize + dedup key
    T->>J: GET /rest/api/3/search (JQL by dedup label)
    alt no existing issue
        T->>J: POST /rest/api/3/issue (create, ADF)
    else existing issue
        T->>J: POST /rest/api/3/issue/{key}/comment (recurrence)
    end
    T->>J: POST /rest/api/3/issue/{key}/transitions
```

## Jira deduplication flow

```mermaid
flowchart TD
    A[Normalized finding] --> B[Generate gd- dedup key]
    B --> C[Build JQL: project AND labels = dedup key]
    C --> D[GET /search]
    D --> E{total > 0?}
    E -->|no| F[Build ADF description + payload]
    F --> G[POST /issue create]
    G --> H[Return new issue key]
    E -->|yes| I[Add recurrence comment]
    I --> J[Update last-seen / severity if increased]
    J --> K[Return existing issue key]
```

## Error-handling flow

```mermaid
flowchart TD
    A[Inbound event] --> B{Valid envelope?}
    B -->|no| R[Reject: malformed-event event]
    B -->|yes| C{Authenticated?}
    C -->|no| R
    C -->|yes| D[Normalize]
    D --> E[Forward / process]
    E --> F{HTTP ok?}
    F -->|retryable: timeout/408/429/5xx| G[Backoff + retry]
    G -->|exhausted| DLQ[Dead-letter queue]
    F -->|permanent 4xx| ERR[Record error, no retry]
    F -->|ok| OK[Success event]
    DLQ --> AL[CloudWatch alarm]
```

## Incident lifecycle

```mermaid
flowchart LR
    A[New] --> B[Triage] --> C[Investigating] --> D[Contained]
    D --> E[Remediated] --> F[Closed]
```
