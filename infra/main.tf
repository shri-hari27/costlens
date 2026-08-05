resource "azurerm_resource_group" "costlens" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    project = "costlens"
    purpose = "devops-portfolio"
  }
}

resource "azurerm_storage_account" "costlens" {
  name                     = "costlensst${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.costlens.name
  location                 = azurerm_resource_group.costlens.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = false
  }

  tags = {
    project = "costlens"
  }
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_storage_container" "cost_snapshots" {
  name                  = "cost-snapshots"
  storage_account_name  = azurerm_storage_account.costlens.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "waste_reports" {
  name                  = "waste-reports"
  storage_account_name  = azurerm_storage_account.costlens.name
  container_access_type = "private"
}
