import json
import logging
from datetime import datetime, timedelta, timezone

from azure.identity import ManagedIdentityCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from azure.storage.blob import BlobServiceClient

import os

SUBSCRIPTION_ID = os.environ.get("SUBSCRIPTION_ID")
STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")


def get_credential():
    return ManagedIdentityCredential(client_id=CLIENT_ID)


def get_blob_service_client():
    credential = get_credential()
    account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=credential)


def query_cost_management():
    """Query Cost Management API for month-to-date spend by resource group and service."""
    credential = get_credential()
    client = CostManagementClient(credential)

    scope = f"/subscriptions/{SUBSCRIPTION_ID}"
    today = datetime.now(timezone.utc)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query_definition = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {
            "from": start_of_month.strftime("%Y-%m-%dT00:00:00Z"),
            "to": today.strftime("%Y-%m-%dT23:59:59Z"),
        },
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {"name": "Cost", "function": "Sum"}
            },
            "grouping": [
                {"type": "Dimension", "name": "ResourceGroupName"}
            ],
        },
    }

    result = client.query.usage(scope, query_definition)

    rows = result.rows or []
    columns = [c.name for c in result.columns]

    resource_groups = []
    total_cost = 0.0

    for row in rows:
        row_dict = dict(zip(columns, row))
        cost = float(row_dict.get("Cost", 0))
        rg_name = row_dict.get("ResourceGroupName", "unknown")
        resource_groups.append({"resourceGroup": rg_name, "cost": round(cost, 2)})
        total_cost += cost

    return {
        "totalCost": round(total_cost, 2),
        "currency": "USD",
        "periodStart": start_of_month.strftime("%Y-%m-%d"),
        "periodEnd": today.strftime("%Y-%m-%d"),
        "byResourceGroup": sorted(resource_groups, key=lambda x: x["cost"], reverse=True),
    }


def query_waste_resources():
    """Query Azure Resource Graph for unattached disks, unassociated public IPs, and running VMs."""
    credential = get_credential()
    client = ResourceGraphClient(credential)

    findings = []

    # Unattached managed disks
    disk_query = """
    Resources
    | where type =~ 'microsoft.compute/disks'
    | where properties.diskState =~ 'Unattached'
    | project name, resourceGroup, location, sizeGb=properties.diskSizeGB, sku=sku.name
    """
    disk_result = client.resources(QueryRequest(subscriptions=[SUBSCRIPTION_ID], query=disk_query))
    for row in (disk_result.data or []):
        size_gb = row.get("sizeGb", 0) or 0
        # Rough estimate: Standard HDD ~$0.05/GB/month, adjust for SKU roughly
        est_monthly = round(size_gb * 0.05, 2)
        findings.append({
            "type": "unattached_disk",
            "name": row.get("name"),
            "resourceGroup": row.get("resourceGroup"),
            "location": row.get("location"),
            "estimatedMonthlyCost": est_monthly,
            "fixCommand": f"az disk delete --name {row.get('name')} --resource-group {row.get('resourceGroup')} --yes"
        })

    # Unassociated public IPs
    ip_query = """
    Resources
    | where type =~ 'microsoft.network/publicipaddresses'
    | where properties.ipConfiguration == '' or isnull(properties.ipConfiguration)
    | project name, resourceGroup, location, sku=sku.name
    """
    ip_result = client.resources(QueryRequest(subscriptions=[SUBSCRIPTION_ID], query=ip_query))
    for row in (ip_result.data or []):
        est_monthly = 3.65  # rough Standard Static Public IP monthly cost estimate
        findings.append({
            "type": "unassociated_public_ip",
            "name": row.get("name"),
            "resourceGroup": row.get("resourceGroup"),
            "location": row.get("location"),
            "estimatedMonthlyCost": est_monthly,
            "fixCommand": f"az network public-ip delete --name {row.get('name')} --resource-group {row.get('resourceGroup')}"
        })

    # Running VMs (informational — flagged for review, not necessarily waste)
    vm_query = """
    Resources
    | where type =~ 'microsoft.compute/virtualmachines'
    | extend powerState = tostring(properties.extended.instanceView.powerState.code)
    | project name, resourceGroup, location, vmSize=properties.hardwareProfile.vmSize, powerState
    """
    vm_result = client.resources(QueryRequest(subscriptions=[SUBSCRIPTION_ID], query=vm_query))
    for row in (vm_result.data or []):
        findings.append({
            "type": "running_vm",
            "name": row.get("name"),
            "resourceGroup": row.get("resourceGroup"),
            "location": row.get("location"),
            "vmSize": row.get("vmSize"),
            "powerState": row.get("powerState"),
            "estimatedMonthlyCost": None,
            "fixCommand": f"az vm deallocate --name {row.get('name')} --resource-group {row.get('resourceGroup')}"
        })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
        "totalFindings": len(findings),
    }


def write_snapshot():
    """Fetch fresh cost + waste data and write both a dated snapshot and latest.json."""
    blob_service = get_blob_service_client()

    cost_data = query_cost_management()
    cost_data["snapshotDate"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    waste_data = query_waste_resources()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Write cost snapshot (dated + latest)
    cost_container = blob_service.get_container_client("cost-snapshots")
    cost_container.upload_blob(f"{date_str}.json", json.dumps(cost_data), overwrite=True)
    cost_container.upload_blob("latest.json", json.dumps(cost_data), overwrite=True)

    # Write waste report (dated + latest)
    waste_container = blob_service.get_container_client("waste-reports")
    waste_container.upload_blob(f"{date_str}.json", json.dumps(waste_data), overwrite=True)
    waste_container.upload_blob("latest.json", json.dumps(waste_data), overwrite=True)

    logging.info(f"Snapshot written for {date_str}: total cost ${cost_data['totalCost']}, {waste_data['totalFindings']} waste findings")

    return cost_data, waste_data
