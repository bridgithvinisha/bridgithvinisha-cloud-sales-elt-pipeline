# Setup and troubleshooting

## GCP setup (optional; cloud phase)

1. In the Google Cloud Console, select an existing project or create one. The
   project ID is globally unique and immutable; it is not the display name.
   Check the project selector and billing page before proceeding. Do not enable
   paid services or attach a billing account unless you understand the account's
   terms and have authorization.
2. Enable BigQuery and Cloud Storage APIs. From PowerShell with the Google Cloud
   CLI installed and an authorized account:

   ```powershell
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable bigquery.googleapis.com storage.googleapis.com --project=YOUR_PROJECT_ID
   ```

3. Choose one region for both resources; this project uses `us-central1` as the
   example. Create a private, uniform-access bucket and a BigQuery dataset in
   that same region. Replace the example names with your own unique values:

   ```powershell
   $env:GCP_PROJECT_ID = "your-project-id"
   $env:GCP_REGION = "us-central1"
   $env:GCS_BUCKET = "your-globally-unique-bucket-name"
   $env:BIGQUERY_DATASET = "sales_elt"
   gcloud storage buckets create "gs://$env:GCS_BUCKET" --project=$env:GCP_PROJECT_ID --location=$env:GCP_REGION --uniform-bucket-level-access --public-access-prevention
   bq --location=$env:GCP_REGION mk --dataset "$($env:GCP_PROJECT_ID):$($env:BIGQUERY_DATASET)"
   ```

4. Set up local Application Default Credentials (ADC), used by the Python
   clients. Install the official Google Cloud CLI, then run:

   ```powershell
   gcloud auth application-default login
   python -m src.check_gcp_auth
   ```

   ADC is distinct from `gcloud auth login`. No service-account key is needed
   or should be committed. For workloads running on Google Cloud, use the
   attached workload identity/service account instead of a downloaded key.
5. Grant the human identity only the permissions it needs. For the current
   upload/status-update flow, use a narrowly scoped custom bucket role with
   object create/get/update permissions (or an approved equivalent). BigQuery
   needs job creation at project scope and data write access on this dataset;
   `roles/bigquery.jobUser` plus dataset-scoped `roles/bigquery.dataEditor` are
   typical starting roles. Dataset/bucket creation may require a separate
   administrator. The BigQuery service agent must be able to read the GCS source
   objects for load jobs. Ask an administrator for these grants; do not grant
   Owner/Editor merely to silence permission errors.
6. Export settings into the current PowerShell session (use the values you
   created above). They are resource identifiers, not credentials. `.env` is
   ignored by Git, but this implementation reads process environment variables
   directly and does not parse `.env` automatically.

## Pricing and no-billing options

Pricing and free limits were checked against Google's official pricing pages on
2026-10-16; prices/eligibility can change, and region, currency, account, and
usage affect charges. The official BigQuery pricing page currently lists a
monthly free usage tier of 10 GiB storage and 1 TiB query processing, plus free
batch-load operations; excess storage/query use is billable. BigQuery Sandbox
can be used without a credit card for BigQuery-only learning, but it does not
provide the GCS bucket required by this end-to-end pipeline and has sandbox
limits. Cloud Storage Always Free currently lists 5 GB-months Standard storage,
5,000 Class A operations, 50,000 Class B operations, and 100 GB of eligible
North American transfer, with eligibility restricted to specified US regions
and other terms. Always Free is not a guarantee that every account or operation
will be free. For a complete GCS + BigQuery run, confirm billing eligibility and
the console's current terms first; no billing account is assumed here.

Authoritative references:

- [BigQuery pricing and free tier](https://cloud.google.com/bigquery/pricing)
- [BigQuery Sandbox](https://cloud.google.com/bigquery/docs/sandbox)
- [Cloud Storage pricing and Always Free limits](https://cloud.google.com/storage/pricing)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Cloud Storage bucket locations](https://cloud.google.com/storage/docs/locations)

For a small sample, standard batch loads avoid streaming insert charges; queries
are on-demand and can benefit from the published free allowance. Avoid capacity
reservations, Cloud Composer, and always-on compute for this portfolio. Configure
budgets/alerts, but remember budget alerts notify; they do not necessarily stop
resources or guarantee a hard spending cap.

## Run cloud ingestion

After the APIs, IAM, bucket, dataset, and ADC have been confirmed:

```powershell
python -m src.run_cloud_pipeline --input data/raw/sales_synthetic.csv
```

The script uploads the original file to an immutable content-addressed GCS path,
batch-loads its raw strings into BigQuery, runs the staging/quarantine and
dimensional `MERGE` scripts, then executes integrity assertions. It marks GCS
object metadata and BigQuery audit status. It has not been executed against a
real GCP project in this workspace; cloud-specific permissions, SQL execution,
cost, and location compatibility therefore remain unverified.

## Common errors

| Symptom | Likely cause | Recovery |
|---|---|---|
| ADC not found | `gcloud auth login` was run, but ADC was not created | Run `gcloud auth application-default login`; then rerun the auth check. |
| Permission denied on bucket | Missing object create/get/update permission, or bucket name mismatch | Verify `GCS_BUCKET` and ask an administrator for the narrow bucket role. |
| BigQuery `Access Denied` | Missing `bigquery.jobs.create` or dataset write permission | Verify project/dataset IDs and request jobUser at project scope plus dataEditor on this dataset. |
| API not enabled | API disabled in the selected project | Enable `bigquery.googleapis.com` and `storage.googleapis.com` in the same project. |
| Dataset/bucket location mismatch | Resources are in incompatible locations | Use matching supported locations; for this sample recreate both in `us-central1` before loading. |
| Invalid bucket name | Bucket names are global and follow stricter naming rules | Use a unique lowercase 3–63 character name; update environment settings. |
| BigQuery load rejects CSV | Header/column order differs from expected source schema or malformed CSV quoting | Compare header to `RAW_SOURCE_COLUMNS`; keep raw source intact and inspect load-job errors. |
| `Already Exists` on object upload | Same content already landed | Expected idempotent behavior; identical content reuses stable ingestion ID. If metadata differs, investigate instead of overwriting. |
| Quality assertion reports failures | Duplicate grain, orphan dimension key, or invalid measure | Inspect `stg_sales_rejected`, then run the named assertions and compare raw/staging/fact counts. |

Do not print environment dumps, credential files, or ADC tokens in issue reports.

## Cleanup checklist

1. Stop any local scheduled process.
2. Delete the GCS bucket and its objects if no longer needed (`gcloud storage
   rm --recursive gs://YOUR_BUCKET` then delete the empty bucket).
3. Delete the BigQuery dataset and its tables only after exporting anything you
   want to keep (`bq rm --recursive --dataset PROJECT:DATASET`).
4. Disable APIs only if no other project workload uses them.
5. Check Billing reports, budgets, and active resources after cleanup. Deleting
   resources prevents future storage use but does not erase already accrued
   charges. Never delete a shared project/bucket/dataset without its owner's
   approval.