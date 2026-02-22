# Hook Pack: Az Read-Only

## Category
az

## Purpose

Intercepts Azure CLI (`az`) commands and only allows read operations. Blocks any command that could modify, create, or delete Azure resources. Useful for development environments where developers need visibility into Azure resources without the ability to make changes.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `az-read-filter` | `pre-command` | Intercept `az` commands; allow only `show`, `list`, `get`, `account show` subcommands | Command matches read-only pattern | Block command; show allowed operations list |
| `az-cli-installed` | `pre-command` | Verify `az` CLI is installed and authenticated | `az account show` returns success | Warn; instruct to install/authenticate az CLI |

## Allowed Operations

- `az * show` — Show details of any resource
- `az * list` — List resources of any type
- `az * get-*` — Get operations (e.g., `get-access-token`)
- `az account show` — Show current account
- `az group list` — List resource groups
- `az resource list` — List all resources

## Blocked Operations

All operations not in the allowed list, including:
- `az * create` — Create any resource
- `az * delete` — Delete any resource
- `az * update` — Update any resource
- `az * start` / `stop` / `restart` — Lifecycle operations
- `az * set-*` — Set operations
- `az deployment *` — Deployment operations

## Configuration

- **Default mode:** enforcing
- **Timeout:** 10 seconds per hook
- **Customization:** Additional allowed or blocked patterns can be defined in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | No | — |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
