# Detailed Setup Guide

This guide takes you from a fresh machine to a running IT Onboarding App with Microsoft Entra sign-in and optional Microsoft Graph provisioning.

## 1. Install The App

Run this as your normal user, not with `sudo`:

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/VIKINGBYTESTECH/Onboard-Users/main/scripts/install-from-github.sh | bash
```

On Linux with systemd, this does all of the following:

- Downloads the latest app to `~/onboard-users`
- Installs backend dependencies
- Installs frontend dependencies
- Builds the frontend
- Creates a local HTTPS certificate
- Installs and starts `onboard-users.service`
- Enables the service so it starts again after reboot

Open:

```text
https://localhost:5174
```

The browser may warn about the certificate. That is expected because the local development certificate is self-signed.

## 2. If The Setup Wizard Does Not Show

The setup wizard shows when this file is missing:

```text
backend/.setup-complete
```

To show the wizard again:

```bash
cd ~/onboard-users
rm -f backend/.setup-complete
systemctl --user restart onboard-users.service
```

Then reopen:

```text
https://localhost:5174
```

## 3. Create The Entra App Registration

Open:

```text
https://entra.microsoft.com
```

Then go to:

```text
Identity > Applications > App registrations > New registration
```

Use these values:

- Name: `IT Onboarding App`
- Supported account types: `Accounts in this organizational directory only`
- Redirect URI platform: `Single-page application (SPA)`
- Redirect URI: `https://localhost:5174`

Click `Register`.

After registration, copy these values from the app overview page:

- `Directory (tenant) ID`
- `Application (client) ID`

You will paste both into the setup wizard.

## 4. Add Redirect URIs

In the App Registration, go to:

```text
Authentication
```

Under `Single-page application`, make sure this URI exists:

```text
https://localhost:5174
```

If you will open the app from another internal URL, add that exact URL too. Examples:

```text
https://your-pc-name:5174
https://your-device.your-tailnet.ts.net:5174
```

Only add HTTP redirect URIs if you intentionally run without HTTPS:

```text
http://localhost:5174
```

## 5. Configure Admin Login

The admin page uses Microsoft sign-in. In the setup wizard, fill in:

- Entra tenant ID: `Directory (tenant) ID`
- Entra client ID: `Application (client) ID`

The app checks that the signed-in admin is allowed to edit controlled option lists.

Recommended role setup:

1. In Entra admin center, go to `Identity > Roles & admins`.
2. Open `User Administrator`.
3. Assign the role to the IT/admin user who will manage onboarding.
4. Sign out and sign back in before testing admin access.

If your tenant does not emit directory role claims in the ID token, use the fallback app-role method:

1. Go to the App Registration.
2. Open `App roles`.
3. Create an app role:
   - Display name: `User Administrator`
   - Value: `User Administrator`
   - Allowed member types: `Users/Groups`
   - Enabled: yes
4. Go to the Enterprise Application for the app.
5. Open `Users and groups`.
6. Assign the `User Administrator` app role to the correct admin user or group.

## 6. Create A Client Secret For Real Provisioning

Skip this section if you only want preview/report mode.

To let the backend create users and update Entra through Microsoft Graph:

1. Open the App Registration.
2. Go to `Certificates & secrets`.
3. Click `New client secret`.
4. Add a description, for example `IT Onboarding local service`.
5. Choose an expiry that matches your policy.
6. Click `Add`.
7. Copy the secret `Value`.

Paste the secret value into the setup wizard as `Entra client secret`.

Do not copy `Secret ID`; the app needs the secret `Value`.

## 7. Add Microsoft Graph Permissions

In the App Registration, go to:

```text
API permissions > Add a permission > Microsoft Graph > Application permissions
```

Add the permissions your tenant policy allows. Typical permissions for full provisioning are:

- `User.ReadWrite.All`
- `GroupMember.ReadWrite.All`
- `Directory.ReadWrite.All`
- `Organization.Read.All`

Then click:

```text
Grant admin consent
```

Admin consent is required for application permissions. Without admin consent, preview mode can still work, but real provisioning will fail.

## 8. Fill Out The Setup Wizard

Open:

```text
https://localhost:5174
```

Fill in:

- Frontend origin: `https://localhost:5174`
- Entra tenant ID
- Entra client ID
- Entra client secret, only if real Graph provisioning should be enabled
- Default user domain, for example `example.com`
- Usage location, for Norway use `NO`
- IT contact email
- Onboarding portal URL
- Company list
- Department list
- Office location list
- Employee type list
- PC model list
- Mobile subscription list

Save the wizard.

The wizard writes:

- `backend/.env`
- `backend/app/data/options.json`
- `backend/.setup-complete`

Restart the service so the backend reloads the new `.env` values:

```bash
systemctl --user restart onboard-users.service
```

## 9. Verify The Service

Check service status:

```bash
systemctl --user status onboard-users.service
```

Follow logs:

```bash
journalctl --user -u onboard-users.service -f
```

Check backend health:

```bash
curl -k https://localhost:8010/health
```

Expected response:

```json
{"status":"ok"}
```

## 10. Test The App Safely

Start with preview mode:

1. Open `https://localhost:5174`.
2. Fill out a test employee.
3. Run preview first.
4. Confirm proposed username, groups, licenses and tasks.

Only run real provisioning when all of these are true:

- Client secret is configured.
- Graph permissions are granted.
- Admin consent is granted.
- HR approval is checked.
- Manager approval is checked.
- `Utfør irreversible Entra-handlinger` is checked.

## 11. Common Problems

### Setup wizard does not show

Remove the setup lock and restart:

```bash
cd ~/onboard-users
rm -f backend/.setup-complete
systemctl --user restart onboard-users.service
```

### Browser blocks the certificate

The local certificate is self-signed. For local testing, continue through the browser warning. For production, put the app behind a real reverse proxy with a trusted certificate.

### Microsoft login says redirect URI is invalid

Add the exact URL shown in the browser to the App Registration as a SPA redirect URI. `https://localhost:5174` and `http://localhost:5174` are different redirect URIs.

### Admin page returns 403

The signed-in user does not have the expected admin role claim. Assign the Entra `User Administrator` role, or configure the app-role fallback named exactly:

```text
User Administrator
```

### Admin page says Entra tenant/client ID is missing

Click `Åpne setup wizard` on the Admin page. The app will reopen the setup wizard so you can enter the Entra values without deleting files manually.

### Real provisioning fails

Check:

- `ENTRA_CLIENT_SECRET` is set.
- API permissions are application permissions, not delegated permissions.
- Admin consent has been granted.
- The default domain exists in the tenant.
- Usage location is a valid two-letter country code, for example `NO`.

## References

- Register an app: https://learn.microsoft.com/en-us/graph/auth-register-app-v2
- Microsoft Graph app-only access: https://learn.microsoft.com/en-us/graph/auth-v2-service
- Microsoft Graph permissions: https://learn.microsoft.com/en-us/graph/permissions-overview
- Configure API permissions: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis
