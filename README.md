# IT Onboarding App

Web app for HR-driven IT onboarding with optional Microsoft Entra ID provisioning through Microsoft Graph.

The app is intentionally safe by default:

- Preview/report mode works without Microsoft credentials.
- Real provisioning only runs when Graph credentials are configured and both HR and manager approval are present.
- The user must explicitly set `execute=true` for irreversible Graph actions.
- Repository defaults are examples only. Local customer-specific config lives in ignored runtime files.

## Structure

- `backend/` - FastAPI API with validation, rules, audit log, and Microsoft Graph integration.
- `frontend/` - React/Vite app for HR input, approvals, preview, execution, and report display.

## Company Field

The HR form includes a controlled company selector. During Entra user creation, the selected value is written to the Microsoft Graph user property `companyName`.

## Admin Page

The frontend has an `ADMIN` button in the top-right corner. The admin page lets authorized users edit the controlled option lists used by the HR form:

- Companies
- Departments
- Office locations
- Employee types
- PC models
- Mobile subscriptions

Admin APIs require Microsoft sign-in and an Entra token for a user with the `User Administrator` directory role. The backend checks the Entra directory role template ID `fe930be7-5e62-47db-91af-98c3a49a38b1`.

For Microsoft login, configure these values:

```bash
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-public-client-or-spa-app-client-id
```

Add the app URL as a SPA redirect URI in Entra, for example:

- `https://localhost:5174`
- `http://localhost:5174` only if you intentionally run without HTTPS
- Your internal/Tailscale URL if you use one

## Microsoft Entra Setup

For a detailed setup guide, see [docs/ENTRA_SETUP.md](docs/ENTRA_SETUP.md).

Create an app registration in Entra ID and grant application permissions appropriate for your tenant policy, for example:

- `User.ReadWrite.All`
- `GroupMember.ReadWrite.All`
- `Directory.ReadWrite.All`
- `Organization.Read.All`

Admin consent is required for application permissions.

Set backend environment variables:

```bash
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-app-client-id
ENTRA_CLIENT_SECRET=your-client-secret
ENTRA_DEFAULT_DOMAIN=example.com
ENTRA_USAGE_LOCATION=NO
```

The app resolves groups by display name. Create or map these groups in Entra:

- `IT-Users`
- `VPN-Users`
- `Intune-Managed`
- `Finance`
- `ERP-Users`
- `CRM-Users`
- `Sales-Team`

Relevant Microsoft Graph documentation:

- Create user: https://learn.microsoft.com/en-us/graph/api/user-post-users
- Add group member: https://learn.microsoft.com/en-us/graph/api/group-post-members
- List subscribed SKUs: https://learn.microsoft.com/en-us/graph/api/subscribedsku-list
- Graph permissions overview: https://learn.microsoft.com/en-us/graph/permissions-overview

## Quick Install

No Git required:

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/VIKINGBYTESTECH/Onboard-Users/main/scripts/install-from-github.sh | bash
```

Run as your normal user, not with `sudo`. On Linux with systemd, the curl installer also installs and starts `onboard-users.service` automatically. Open `https://localhost:5174` when it finishes.

To install without creating the service:

```bash
curl -fsSL https://raw.githubusercontent.com/VIKINGBYTESTECH/Onboard-Users/main/scripts/install-from-github.sh | bash -s -- --no-service
```

If you already downloaded the repo, run the same local install and service setup manually:

```bash
chmod +x scripts/*.sh
./scripts/install.sh
./scripts/install-service.sh
```

Open `https://localhost:5174`.

For temporary development without service, start the app manually:

```bash
HTTPS=true ./scripts/run-dev.sh
```

Both service and dev mode create a self-signed development certificate in `.certs/`. Your browser will warn the first time because the certificate is local and self-signed.

## Run As A Service

On Linux with systemd, install the app as a user service so it starts again after reboot:

```bash
./scripts/install-service.sh
```

The service uses HTTPS by default and serves `https://localhost:5174`.

Useful commands:

```bash
systemctl --user status onboard-users.service
journalctl --user -u onboard-users.service -f
systemctl --user restart onboard-users.service
```

To remove the service:

```bash
./scripts/uninstall-service.sh
```

The installer creates local ignored config files, installs dependencies, and asks for Entra values. Leave Entra fields empty for preview-only mode.

You can also start the app without completing CLI setup. If `backend/.setup-complete` is missing, the frontend shows a first-run setup wizard that writes:

- `backend/.env`
- `backend/app/data/options.json`
- `backend/.setup-complete`

Restart the backend after completing the wizard so environment values are reloaded.

To run the wizard again locally:

```bash
rm backend/.setup-complete
```

## Manual Run

Use this only for development or troubleshooting without service.

Create local config files and start both backend and frontend:

```bash
chmod +x scripts/bootstrap-local.sh
./scripts/bootstrap-local.sh
HTTPS=true ./scripts/run-dev.sh
```

Open `https://localhost:5174`.

## Check Build

```bash
./scripts/check.sh
```

## API

- `GET /health`
- `GET /api/config`
- `POST /api/onboarding/preview`
- `POST /api/onboarding/run`

Use `/api/onboarding/preview` for validation, proposed username, groups, licenses, equipment, tasks, welcome mail draft, and report without making Graph changes.

Use `/api/onboarding/run` only after approvals and with `execute=true`.
