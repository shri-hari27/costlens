resource "azurerm_kubernetes_cluster" "costlens" {
  name                = "costlens-aks"
  location            = azurerm_resource_group.costlens.location
  resource_group_name = azurerm_resource_group.costlens.name
  dns_prefix          = "costlens-aks"
  kubernetes_version  = null

  default_node_pool {
    name       = "default"
    node_count = var.aks_node_count
    vm_size    = var.aks_vm_size
  }

  identity {
    type = "SystemAssigned"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  network_profile {
    network_plugin = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    project = "costlens"
  }
}

output "aks_oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.costlens.oidc_issuer_url
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.costlens.name
}
