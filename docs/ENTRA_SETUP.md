# Microsoft Entra Setup

This app can run in preview mode without Entra. Configure Entra when you want:

- Microsoft sign-in for the admin page.
- Role-gated admin access for users with the `User Administrator` directory role.
- Microsoft Graph provisioning of users, group membership, and licenses.

## 1. Create App Registration

1. Open Microsoft Entra admin center.
2. Go to **Identity > Applications > App registrations**.
3. Create a new registration.
4. Use a single-tenant app unless you explicitly need multi-tenant.
5. Add SPA redirect URIs for the frontend:
   - `http://localhost:5174`
   - Any internal/Tailscale URL you use, for example `http://100.x.x.x:5174`

Save these values:

- Directory tenant ID
- Application client ID

## 2. Configure Admin Login

Set these in `backend/.env`:

```bash
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-app-client-id
```

The backend checks for the Entra `User Administrator` directory role using template ID:

```text
fe930be7-5e62-47db-91af-98c3a49a38b1
```

If your tenant does not emit directory role claims in ID tokens, configure optional claims or use an app role named `User Administrator` and assign it only to the correct admins.

## 3. Configure Graph Provisioning

For real user provisioning, create a client secret and set:

```bash
ENTRA_CLIENT_SECRET=your-client-secret
ENTRA_DEFAULT_DOMAIN=example.com
ENTRA_USAGE_LOCATION=NO
```

Grant application permissions according to your tenant policy, then admin-consent them. Typical permissions for this app are:

- `User.ReadWrite.All`
- `GroupMember.ReadWrite.All`
- `Directory.ReadWrite.All`
- `Organization.Read.All`

Use least privilege in production. If you only want preview/report mode, do not set `ENTRA_CLIENT_SECRET`.

## 4. Local Config Files

Use the installer:

```bash
./scripts/install.sh
```

Or use the browser setup wizard. Start the backend/frontend and open the app. If `backend/.setup-complete` is missing, the wizard will collect runtime values, Entra IDs, and option lists, then write local config files.

Or create config files without installing dependencies:

```bash
./scripts/bootstrap-local.sh
```

This creates:

- `backend/.env`
- `frontend/.env.local`
- `backend/app/data/options.json`

These files are local runtime config and are ignored by Git.

## References

- Create users: https://learn.microsoft.com/en-us/graph/api/user-post-users
- Add group members: https://learn.microsoft.com/en-us/graph/api/group-post-members
- List subscribed SKUs: https://learn.microsoft.com/en-us/graph/api/subscribedsku-list
- Microsoft Graph permissions: https://learn.microsoft.com/en-us/graph/permissions-overview
