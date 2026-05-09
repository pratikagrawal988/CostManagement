# CSP Native APIs — Reference Guide

This document describes how FinOps connects to cloud-provider monitoring APIs, what data each API exposes, and how to configure credentials in the **Integrations** tab.

---

## What Are CSP Native APIs?

Each major cloud provider exposes a first-party monitoring and metrics API. FinOps queries these APIs at scheduled intervals to retrieve resource utilisation, performance, and cost signals used by the Recommendation Engine.

| Cloud | API Name | Protocol |
|-------|----------|----------|
| AWS | Amazon CloudWatch | REST (AWS Sig v4) |
| Azure | Azure Monitor Metrics API | REST (OAuth 2.0) |
| GCP | Google Cloud Monitoring | REST / gRPC (OAuth 2.0) |
| OCI | OCI Monitoring | REST (API Key / OCI Sig v1) |

---

## AWS — Amazon CloudWatch

### Endpoint

```
https://monitoring.{region}.amazonaws.com
```

### Authentication Method

FinOps uses **cross-account IAM Role assumption** via AWS STS. The customer creates a dedicated IAM Role in their AWS account, trusts FinOps's AWS account, and provides the Role ARN + External ID.

### Setup Steps

1. Log in to the AWS Console of the target account.
2. Go to **IAM → Roles → Create Role**.
3. Choose **Another AWS Account** and enter **FinOps's account ID** (provided during onboarding).
4. Set an **External ID** (a random string you share with FinOps — prevents confused-deputy attacks).
5. Attach the policy below.
6. Copy the **Role ARN** and enter it in the Integrations tab alongside the External ID and default region.

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "rds:DescribeDBInstances",
        "s3:ListAllMyBuckets",
        "sts:AssumeRole"
      ],
      "Resource": "*"
    }
  ]
}
```

### Credential Fields (Integrations Tab)

| Field | Description |
|-------|-------------|
| IAM Role ARN | e.g. `arn:aws:iam::123456789012:role/FinOpsMonitoringRole` |
| External ID | Random string shared during onboarding |
| Default Region | e.g. `us-east-1` |

### Rate Limits

- `GetMetricData`: 1,500 req/sec per account
- `GetMetricStatistics`: 400 req/sec per account

### Official Docs

<https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/>

---

## Azure — Azure Monitor Metrics API

### Endpoint

```
https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroup}/providers/{resourceType}/{resourceName}/providers/microsoft.insights/metrics
```

### Authentication Method

FinOps uses an **Azure Service Principal** with the Client Credentials OAuth 2.0 flow. The customer registers an app in Entra ID (formerly Azure AD) and grants it the built-in **Monitoring Reader** role.

### Setup Steps

1. Open **Azure Portal → Entra ID → App Registrations → New Registration**.
2. Name the app (e.g. `finops-monitor`) and copy the **Application (Client) ID** and **Tenant (Directory) ID**.
3. Under **Certificates & Secrets**, create a new **Client Secret** and note the value (shown once).
4. In **Subscriptions → Access Control (IAM)**, assign the role **Monitoring Reader** to the app at the subscription scope.
5. Enter all four values in the Integrations tab. The client secret is stored encrypted in FinOps's Vault.

### Required RBAC Role

```
Monitoring Reader  (built-in)
Reader             (on target subscription or resource groups)
```

### Credential Fields (Integrations Tab)

| Field | Description |
|-------|-------------|
| Tenant (Directory) ID | GUID from Entra ID |
| Application (Client) ID | GUID of the registered app |
| Client Secret | Write-only; stored in Vault |
| Subscription ID | Target Azure subscription GUID |

### Rate Limits

- 12,000 read requests / hour per subscription

### Official Docs

<https://learn.microsoft.com/en-us/rest/api/monitor/metrics/list>

---

## GCP — Google Cloud Monitoring API

### Endpoint

```
https://monitoring.googleapis.com/v3/projects/{projectId}/timeSeries
```

### Authentication Method

FinOps uses a **GCP Service Account** with either a JSON key file or **Workload Identity Federation** (preferred in production to avoid long-lived credentials).

### Setup Steps

1. In **GCP Console → IAM & Admin → Service Accounts**, create a new service account (e.g. `finops-monitor@{project}.iam.gserviceaccount.com`).
2. Grant it the following roles at the project level:
   - `roles/monitoring.viewer`
   - `roles/compute.viewer`
   - `roles/cloudsql.viewer`
3. If using a JSON key: create a **JSON key** under the service account's **Keys** tab, download it, and provide it to FinOps (base64-encoded). **Use Workload Identity in production.**
4. Enter the Project ID and service account email in the Integrations tab.

### Credential Fields (Integrations Tab)

| Field | Description |
|-------|-------------|
| GCP Project ID | e.g. `my-project-123` |
| Service Account Email | Full service account email |
| JSON Key (base64) | Write-only; stored in Vault — leave blank when using Workload Identity |

### Rate Limits

- 6,000 read requests / minute per project

### Official Docs

<https://cloud.google.com/monitoring/api/ref_v3/rest>

---

## OCI — Oracle Cloud Infrastructure Monitoring

### Endpoint

```
https://telemetry.{region}.oraclecloud.com/20180401/metrics/actions/summarizeMetricsData
```

### Authentication Method

FinOps uses **OCI API Key authentication** (RSA key pair). The customer creates a dedicated OCI user, uploads the public key, and shares the OCID + fingerprint with FinOps.

### Setup Steps

1. In **OCI Console → Identity → Users**, create a new user (e.g. `finops-monitoring`).
2. Generate an RSA key pair (4096-bit). Upload the **public key** to the user under **API Keys**.
3. Note the **Fingerprint** displayed after upload.
4. Create a group (e.g. `FinOps-Group`), add the user to it, and apply the policy below in the target compartment.
5. Enter all credential fields in the Integrations tab. The private key PEM is stored encrypted in FinOps's Vault.

### Required OCI Policy

```
Allow group FinOps-Group to read metrics in tenancy
Allow group FinOps-Group to inspect instances in tenancy
Allow group FinOps-Group to inspect volumes in tenancy
```

### Credential Fields (Integrations Tab)

| Field | Description |
|-------|-------------|
| Tenancy OCID | `ocid1.tenancy.oc1..aaa…` |
| User OCID | `ocid1.user.oc1..aaa…` |
| Key Fingerprint | `xx:xx:xx:…` (16 colon-separated hex pairs) |
| Private Key PEM | Write-only; stored in Vault |
| Home Region | e.g. `us-ashburn-1` |

### Rate Limits

- ~10 requests / second (varies by operation)

### Official Docs

<https://docs.oracle.com/en-us/iaas/api/#/en/monitoring/20180401/>

---

## Configuring Credentials in FinOps

All credential fields are managed in the **Integrations** tab of the Recommendation Engine:

1. Open the **Integrations** tab (top navigation, 🔗 icon).
2. Select the **☁️ CSP Native APIs** sub-tab.
3. Click the CSP (AWS / Azure / GCP / OCI) you want to configure.
4. Fill in the credential fields in **Section A — Credentials & Connection Status**.
5. Click **Test Connection** to validate connectivity (two-stage: auth then data pull — see below).
6. Click **Save Credentials** to persist the changes.

> Secrets (client secrets, JSON keys, private key PEMs) are write-only in the UI and stored encrypted in FinOps's HashiCorp Vault. They cannot be retrieved after saving — only replaced.

---

## Two-Stage Test Connection

When you click **Test Connection** for any CSP, the system performs two sequential checks:

### Stage 1 — Authentication Check
Attempts to authenticate using the stored credentials (STS AssumeRole for AWS, OAuth client-credentials for Azure/GCP, API Key for OCI). The button shows `1/2 Checking auth…` during this phase.

**Success condition:** The API returns a valid auth token / session without error.

**Failure:** If auth fails, the button shows `✗ Connection Failed` with an error card explaining the cause (bad credentials, network unreachable, role not found, etc.). The second stage is not attempted.

### Stage 2 — Sample Metric Pull (Customer 636)
If auth succeeds, FinOps immediately issues a single metric data request for **demo customer 636** to verify the full pipeline: credential → API → metric retrieval → data received. The button shows `2/2 Pulling sample metric…` during this phase.

**Sample metrics pulled per CSP:**

| CSP | Metric | Namespace | Resource |
|-----|--------|-----------|----------|
| AWS | `CPUUtilization` | `AWS/EC2` | `i-0a3f7c8b91d2e4567` |
| Azure | `Percentage CPU` | `Microsoft.Compute/virtualMachines` | `vm-prod-api-west-02` |
| GCP | `compute.googleapis.com/instance/cpu/utilization` | `compute.googleapis.com` | `instance-gcp-us-c1` |
| OCI | `CpuUtilization` | `oci_computeagent` | `ocid1.instance.oc1..abc` |

**On success:** A result card is shown inline displaying: Auth OK · metric name · sample value · resource ID · region · query latency.

**Purpose:** This two-stage validation confirms end-to-end data access, not just authentication, before the recommendation engine can use the integration for real-time metric evaluation.

---

## FinOps Observability — Validate Pipeline

For the **FinOps Observability (Elasticsearch)** source, a separate **Validate Pipeline** button is available in the Integrations tab:

### What It Does
1. Resolves the configured index pattern template using **customer ID 636** and the current date (e.g. `finops-636-vm-metrics-2026.03`).
2. Issues a sample Elasticsearch query against the resolved index.
3. Returns: resolved index name · document count · a sample field/value pair · query latency.

### Result Card Fields

| Field | Description |
|-------|-------------|
| Resolved Index | Full index name with runtime variables substituted (e.g. `finops-636-vm-metrics-2026.03`) |
| Record Count | Number of documents found in the index |
| Sample Field | A representative field and its value (e.g. `cpu_utilization_pct = 3.2`) |
| Query Latency | Round-trip time from FinOps to Elasticsearch |

**Purpose:** Confirms that the index naming convention is correct, the customer 636 data exists, and the field schema matches expectations — before configuring metrics in the recommendation wizard.

---

## Metric Onboarding

The Integrations tab shows a read-only metric catalog drawn from each CSP's supported namespaces. Adding new namespaces or metrics to the catalog is handled in the **Metric Onboarding** menu (coming soon). New metrics are not configured inside the Recommendation wizard; they must be onboarded first.

---

## Credential Security Model

| Concern | Approach |
|---------|----------|
| Secret storage | HashiCorp Vault (AES-256 encryption at rest) |
| Secret transit | TLS 1.3 in-transit; never logged |
| AWS secret rotation | IAM Role keys rotate automatically via STS |
| Azure secret rotation | Client secrets should be rotated every 90 days via Entra ID |
| GCP secret rotation | Prefer Workload Identity (keyless); rotate JSON keys via IAM API |
| OCI secret rotation | Generate a new key pair in OCI Console and re-upload |
| Least privilege | Each service account / role is scoped to read-only monitoring permissions |
