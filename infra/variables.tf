variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name prefix used in resource naming"
  type        = string
  default     = "costlens"
}

variable "resource_group_name" {
  description = "Name of the resource group for CostLens resources"
  type        = string
  default     = "costlens-rg"
}

variable "aks_node_count" {
  description = "Number of nodes in the AKS default pool (limited to 1 by remaining 2-vCPU regional quota)"
  type        = number
  default     = 1
}

variable "aks_vm_size" {
  description = "VM size for AKS nodes (only v7-generation SKUs allowed on this subscription)"
  type        = string
  default     = "Standard_D2ads_v7"
}
