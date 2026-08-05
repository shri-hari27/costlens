# Storage account required by the Function App itself (separate from our data storage account)
resource "azurerm_storage_account" "function_storage" {
  name                     = "costlensfnst${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.costlens.name
  location                 = "centralindia"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_service_plan" "function_plan" {
  name                = "costlens-function-plan"
  resource_group_name = azurerm_resource_group.costlens.name
  location            = "centralindia"
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "costlens" {
  name                       = "costlens-func-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.costlens.name
  location                   = "centralindia"
  storage_account_name       = azurerm_storage_account.function_storage.name
  storage_account_access_key = azurerm_storage_account.function_storage.primary_access_key
  service_plan_id            = azurerm_service_plan.function_plan.id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function_identity.id]
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "AZURE_CLIENT_ID"          = azurerm_user_assigned_identity.function_identity.client_id
    "STORAGE_ACCOUNT_NAME"     = azurerm_storage_account.costlens.name
    "SUBSCRIPTION_ID"          = "ed77ab03-a5af-4616-9580-7c3766e5f7ca"
    "FUNCTIONS_WORKER_RUNTIME" = "python"
  }

  tags = {
    project = "costlens"
  }
}

output "function_app_name" {
  value = azurerm_linux_function_app.costlens.name
}

output "function_app_default_hostname" {
  value = azurerm_linux_function_app.costlens.default_hostname
}
