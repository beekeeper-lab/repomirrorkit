# Hook Pack: Az Limited-Ops

## Category
az

## Purpose

Allows common Azure deployment operations while blocking destructive commands. Provides a balanced approach for teams that need to deploy to Azure but should not be able to delete resource groups, VMs, or storage accounts.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `az-ops-filter` | `pre-command` | Intercept `az` commands; allow deployment ops, block destructive ops | Command matches allowed pattern and does not match blocked pattern | Block command; show what was blocked and why |
| `az-cli-installed` | `pre-command` | Verify `az` CLI is installed and authenticated | `az account show` returns success | Warn; instruct to install/authenticate az CLI |

## Allowed Operations

All read operations (same as az-read-only), plus:
- `az webapp deploy` — Deploy to App Service
- `az webapp config *` — Configure App Service
- `az functionapp deploy` — Deploy Azure Function
- `az functionapp config *` — Configure Azure Function
- `az acr build` — Build container image in ACR
- `az acr login` — Authenticate to ACR
- `az storage blob upload*` — Upload blobs
- `az keyvault secret set` — Set Key Vault secrets
- `az webapp create` — Create App Service (non-destructive)
- `az functionapp create` — Create Function App (non-destructive)

## Blocked Operations

- `az group delete` — Delete resource group (cascading delete)
- `az vm delete` — Delete virtual machine
- `az storage account delete` — Delete storage account
- `az sql server delete` — Delete SQL server
- `az sql db delete` — Delete SQL database
- `az keyvault delete` — Delete Key Vault
- `az network vnet delete` — Delete virtual network
- `az aks delete` — Delete AKS cluster
- `az * purge` — Purge soft-deleted resources

## Configuration

- **Default mode:** enforcing
- **Timeout:** 10 seconds per hook
- **Customization:** Additional allowed or blocked patterns can be defined in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | advisory |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
