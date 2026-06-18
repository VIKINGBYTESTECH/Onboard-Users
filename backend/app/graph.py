from typing import Any

import httpx

from .config import Settings
from .schemas import OnboardingInput


LICENSE_SKU_PARTS = {
    "Microsoft 365 Business Premium": ["SPB"],
    "Power BI Pro": ["POWER_BI_PRO"],
    "Intune": ["INTUNE_A", "EMS"],
    "Defender for Endpoint": ["Microsoft_365_Defender", "WIN_DEF_ATP"],
}


class GraphProvisioner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _token(self) -> str:
        url = f"https://login.microsoftonline.com/{self.settings.entra_tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.settings.entra_client_id,
            "client_secret": self.settings.entra_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]

    async def _request(self, method: str, path: str, token: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method,
                f"{self.settings.graph_base_url}{path}",
                headers=headers,
                **kwargs,
            )
            if response.status_code == 204:
                return {"status": 204}
            response.raise_for_status()
            return response.json()

    async def create_user(self, employee: OnboardingInput, username: str, password: str, token: str) -> dict[str, Any]:
        mail_nickname = username.split("@", 1)[0].replace(".", "")
        payload = {
            "accountEnabled": True,
            "displayName": employee.full_name,
            "mailNickname": mail_nickname,
            "userPrincipalName": username,
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": password,
            },
            "jobTitle": employee.job_title,
            "department": employee.department,
            "companyName": employee.company,
            "officeLocation": employee.office_location,
            "employeeType": employee.employee_type,
            "usageLocation": self.settings.entra_usage_location,
        }
        return await self._request("POST", "/users", token, json=payload)

    async def find_group(self, display_name: str, token: str) -> dict[str, Any] | None:
        escaped = display_name.replace("'", "''")
        result = await self._request(
            "GET",
            f"/groups?$filter=displayName eq '{escaped}'&$select=id,displayName",
            token,
        )
        values = result.get("value", [])
        return values[0] if values else None

    async def add_user_to_group(self, user_id: str, group_name: str, token: str) -> dict[str, Any]:
        group = await self.find_group(group_name, token)
        if not group:
            return {"group": group_name, "status": "not_found"}
        await self._request(
            "POST",
            f"/groups/{group['id']}/members/$ref",
            token,
            json={"@odata.id": f"{self.settings.graph_base_url}/directoryObjects/{user_id}"},
        )
        return {"group": group_name, "status": "added", "group_id": group["id"]}

    async def assign_licenses(self, user_id: str, license_names: list[str], token: str) -> list[dict[str, Any]]:
        subscribed = await self._request("GET", "/subscribedSkus?$select=skuId,skuPartNumber", token)
        by_part = {sku["skuPartNumber"]: sku["skuId"] for sku in subscribed.get("value", [])}
        add_licenses = []
        results = []
        for name in license_names:
            sku_id = None
            for part in LICENSE_SKU_PARTS.get(name, []):
                if part in by_part:
                    sku_id = by_part[part]
                    break
            if sku_id:
                add_licenses.append({"skuId": sku_id})
                results.append({"license": name, "status": "queued", "skuId": sku_id})
            else:
                results.append({"license": name, "status": "sku_not_found"})
        if add_licenses:
            await self._request(
                "POST",
                f"/users/{user_id}/assignLicense",
                token,
                json={"addLicenses": add_licenses, "removeLicenses": []},
            )
            for result in results:
                if result["status"] == "queued":
                    result["status"] = "assigned"
        return results

    async def provision(
        self,
        employee: OnboardingInput,
        username: str,
        password: str,
        groups: list[str],
        licenses: list[str],
    ) -> list[dict[str, Any]]:
        token = await self._token()
        results: list[dict[str, Any]] = []
        user = await self.create_user(employee, username, password, token)
        user_id = user["id"]
        results.append({"action": "create_user", "status": "created", "id": user_id, "userPrincipalName": username})
        for group in groups:
            results.append({"action": "add_group", **await self.add_user_to_group(user_id, group, token)})
        for result in await self.assign_licenses(user_id, licenses, token):
            results.append({"action": "assign_license", **result})
        return results
