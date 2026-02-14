# Environment Matrix: [Project Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [DevOps Lead / Platform Engineer]        |
| Related Links  | [Infrastructure repo, runbook, ADR]      |
| Status         | Draft / Reviewed / Approved              |

---

## 1. Environment Inventory

*List every environment, its purpose, and ownership. Keep this table current -- review monthly.*

| Environment | Purpose               | URL / Endpoint               | Owner         | Provisioning Method   | Last Verified |
|-------------|-----------------------|------------------------------|---------------|-----------------------|---------------|
| Development | Local/shared dev work | [https://dev.example.com]    | [Name/Team]   | [IaC / manual / CLI]  | [YYYY-MM-DD]  |
| CI          | Automated testing     | [Ephemeral / URL]            | [Name/Team]   | [IaC / pipeline]      | [YYYY-MM-DD]  |
| Staging     | Pre-prod validation   | [https://staging.example.com]| [Name/Team]   | [IaC / manual]        | [YYYY-MM-DD]  |
| Production  | Live user traffic     | [https://app.example.com]    | [Name/Team]   | [IaC / manual]        | [YYYY-MM-DD]  |
| [Add rows]  |                       |                              |               |                       |               |

---

## 2. Configuration Comparison

*Document key differences between environments. Highlight anything that could cause environment-specific bugs.*

| Configuration Item       | Development        | Staging            | Production         |
|--------------------------|--------------------|--------------------|---------------------|
| Instance/container count | [1]                | [2]                | [N]                 |
| CPU / Memory             | [spec]             | [spec]             | [spec]              |
| Database engine/version  | [engine vX.Y]      | [engine vX.Y]      | [engine vX.Y]       |
| Database size (approx)   | [seed data]        | [copy of prod]     | [live data]         |
| Log level                | [DEBUG]            | [INFO]             | [WARN]              |
| Feature flags            | [all enabled]      | [matches prod]     | [controlled]        |
| TLS certificate source   | [self-signed]      | [managed cert]     | [managed cert]      |
| External service mode    | [mocked/sandbox]   | [sandbox]          | [live]              |
| [Add rows as needed]     |                    |                    |                     |

---

## 3. Secrets Inventory

*List secret names and locations only. Never record secret values in this document.*

| Secret Name                | Environment(s) | Storage Location             | Rotation Schedule  | Owner         |
|----------------------------|----------------|------------------------------|--------------------|---------------|
| [DATABASE_URL]             | All            | [Vault / env var / config]   | [90 days]          | [Name/Team]   |
| [API_KEY_EXTERNAL_SVC]     | Staging, Prod  | [Vault / env var / config]   | [180 days]         | [Name/Team]   |
| [TLS_CERT_PRIVATE_KEY]     | Staging, Prod  | [Cert manager / Vault]       | [Auto-renewal]     | [Name/Team]   |
| [Add rows as needed]       |                |                              |                    |               |

---

## 4. Health Check Endpoints

*List the health/readiness/liveness endpoints for each environment.*

| Environment | Health Endpoint          | Expected Response     | Check Frequency |
|-------------|--------------------------|----------------------|-----------------|
| Development | [/health]                | [200 OK + JSON body] | [Manual]        |
| Staging     | [/health]                | [200 OK + JSON body] | [Every 60s]     |
| Production  | [/health]                | [200 OK + JSON body] | [Every 30s]     |
| Production  | [/readiness]             | [200 OK]             | [Every 30s]     |

---

## 5. Environment Drift Checks

*Track whether environments have diverged from their intended state.*

| Check                                    | Method                       | Frequency    | Last Run     | Status    |
|------------------------------------------|------------------------------|--------------|--------------|-----------|
| IaC plan shows no diff                   | [Terraform plan / Pulumi]    | [Weekly]     | [YYYY-MM-DD] | [Clean / Drift detected] |
| Config values match expected             | [Script / manual audit]      | [Monthly]    | [YYYY-MM-DD] | [Clean / Drift detected] |
| Software versions match across envs      | [Version endpoint check]     | [Per deploy] | [YYYY-MM-DD] | [Clean / Drift detected] |
| Secrets exist and are not expired        | [Vault audit / script]       | [Monthly]    | [YYYY-MM-DD] | [Clean / Drift detected] |

---

## Definition of Done

- [ ] All environments listed with current URLs and owners
- [ ] Configuration differences documented and reviewed
- [ ] Secrets inventory complete (names only, no values)
- [ ] Health check endpoints verified for every environment
- [ ] Drift check schedule established and first run completed
- [ ] Document reviewed and approved by environment owners
