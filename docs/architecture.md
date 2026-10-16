# Architecture and implementation status

## Implemented and locally tested: batch foundation

```mermaid
flowchart LR
    CSV[Immutable source CSV] --> PY[Python extract and profile]
    PY --> VAL[Validate, normalize, quarantine]
    VAL --> CLEAN[Cleaned sales CSV]
    VAL --> REJECT[Rejected rows CSV]
    VAL --> QA[JSON quality summary]
```

The local foundation is deliberately independent of cloud credentials. It
establishes source rules and repeatable outputs before cloud resources are added.

## Implemented in code/SQL; not cloud-tested

```mermaid
flowchart LR
    CSV[Sales CSV] --> PY[Python ingestion]
    PY --> GCS[GCS raw landing]
    GCS --> BQRAW[BigQuery raw]
    BQRAW --> STG[BigQuery staging SQL]
    STG --> DIM[Customer, product, date dimensions]
    STG --> FACT[Sales fact]
    FACT --> BI[Analytics SQL]
```

GCS upload, BigQuery raw batch load, audit records, staging/quarantine SQL,
dimensional `MERGE`s, fact upsert, and analytics/query assertions are implemented
in the source, SQL, and data-model docs. No GCP project was configured here:
permissions, region compatibility, SQL behavior, costs, and end-to-end integration
remain unverified. Orchestration and alerting remain future work.