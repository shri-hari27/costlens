# Identity for the Function App - broad read access to Cost Management + Resource Graph + Storage write
resource "azurerm_user_assigned_identity" "function_identity" {
  name                = "costlens-function-identity"
  resource_group_name = azurerm_resource_group.costlens.name
  location            = azurerm_resource_group.costlens.location
}

resource "azurerm_role_assignment" "function_cost_reader" {
  scope                = "/subscriptions/ed77ab03-a5af-4616-9580-7c3766e5f7ca"
  role_definition_name = "Cost Management Reader"
  principal_id         = azurerm_user_assigned_identity.function_identity.principal_id
}

resource "azurerm_role_assignment" "function_reader" {
  scope                = "/subscriptions/ed77ab03-a5af-4616-9580-7c3766e5f7ca"
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.function_identity.principal_id
}

resource "azurerm_role_assignment" "function_storage_contributor" {
  scope                = azurerm_storage_account.costlens.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_identity.principal_id
}

# Identity for the AKS backend pod - read-only access to Blob Storage ONLY
resource "azurerm_user_assigned_identity" "backend_identity" {
  name                = "costlens-backend-identity"
  resource_group_name = azurerm_resource_group.costlens.name
  location            = azurerm_resource_group.costlens.location
}

resource "azurerm_role_assignment" "backend_storage_reader" {
  scope                = azurerm_storage_account.costlens.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.backend_identity.principal_id
}

# Federated credential: links the AKS backend's Kubernetes ServiceAccount to the backend identity via Workload Identity
resource "azurerm_federated_identity_credential" "backend_fic" {
  name                = "costlens-backend-fic"
  resource_group_name = azurerm_resource_group.costlens.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.costlens.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.backend_identity.id
  subject             = "system:serviceaccount:default:costlens-backend-sa"
}

output "function_identity_client_id" {
  value = azurerm_user_assigned_identity.function_identity.client_id
}

output "backend_identity_client_id" {
  value = azurerm_user_assigned_identity.backend_identity.client_id
}
