import React, { useState, useEffect } from 'react'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import Header from '../components/Header'
import CollapsedSidebar from '../components/CollapsedSidebar'
import DependencyModal from '../components/DependencyModal'
import ConfirmationModal from '../components/ConfirmationModal'
import EditModal from '../components/EditModal'
import CreateModal from '../components/CreateModal'
import BulkEditModal from '../components/BulkEditModal'
import BackToTop from '../components/BackToTop'
import ToastContainer from '../components/ToastContainer'
import IntegrationLogo from '../components/IntegrationLogo'
import { useToast } from '../hooks/useToast'
import { useConfirmation } from '../hooks/useConfirmation'
import { statusesApi, integrationsApi } from '../services/etlApiService'

interface StatusMapping {
  id: number
  status_from: string
  status_to: string
  category?: string  // Changed from status_category to match API response
  integration_name?: string
  integration_id?: number
  integration_logo?: string
  active: boolean
}

interface Integration {
  id: number
  name: string
  integration_type: string
  logo_filename?: string
  active: boolean
}

interface StatusCategory {
  id: number
  name: string
  active: boolean
}

interface StatusesMappingsPageProps {
  embedded?: boolean
}

const StatusesMappingsPage: React.FC<StatusesMappingsPageProps> = ({ embedded = false }) => {
  const [mappings, setMappings] = useState<StatusMapping[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [categories, setCategories] = useState<StatusCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Filter states
  const [statusFromFilter, setStatusFromFilter] = useState('')
  const [statusToFilter, setStatusToFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [integrationFilter, setIntegrationFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Sort states
  const [sortField, setSortField] = useState<string | null>('status_from')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  // Sort handler
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // Edit modal state
  const [editModal, setEditModal] = useState({
    isOpen: false,
    mapping: null as StatusMapping | null
  })

  // Create modal state
  const [createModal, setCreateModal] = useState({
    isOpen: false
  })

  // Bulk edit state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkEditModal, setBulkEditModal] = useState({
    isOpen: false
  })

  // Dependency modal state
  const [dependencyModal, setDependencyModal] = useState({
    isOpen: false,
    mappingId: null as number | null,
    mappingName: '',
    action: 'deactivate' as 'deactivate' | 'activate',
    dependencies: [] as any[],
    reassignmentTargets: [] as any[]
  })

  // Handler functions
  const checkDependencies = async (mappingId: number): Promise<any> => {
    try {
      // TODO: Implement actual dependency checking API call
      return {
        has_dependencies: Math.random() > 0.7,
        dependency_count: Math.floor(Math.random() * 3) + 1,
        affected_items_count: Math.floor(Math.random() * 10) + 1,
        reassignment_targets: mappings.filter(m => m.id !== mappingId && m.active).slice(0, 3)
      }
    } catch (error) {
      console.error('Error checking dependencies:', error)
      throw new Error('Failed to check dependencies')
    }
  }

  const handleToggleActive = async (mappingId: number, currentActive: boolean) => {
    try {
      const mapping = mappings.find(m => m.id === mappingId)
      if (!mapping) return

      if (currentActive) {
        // Deactivating - check for dependencies
        const dependencyData = await checkDependencies(mappingId)

        if (dependencyData.has_dependencies) {
          setDependencyModal({
            isOpen: true,
            mappingId,
            mappingName: `${mapping.status_from} → ${mapping.status_to}`,
            action: 'deactivate',
            dependencies: dependencyData.dependent_mappings || [],
            reassignmentTargets: dependencyData.reassignment_targets || []
          })
          return
        }
      }

      // No dependencies or activating - proceed directly
      await performToggle(mappingId, !currentActive)
    } catch (error) {
      console.error('Error toggling mapping:', error)
      showError('Toggle Failed', 'Failed to toggle mapping status. Please try again.')
    }
  }

  const performToggle = async (mappingId: number, newActiveState: boolean) => {
    try {
      // TODO: Implement actual API call when backend endpoint is ready
      // For now, just update local state after a small delay to simulate API call
      await new Promise(resolve => setTimeout(resolve, 100))

      // Update local state only after "API call" succeeds
      setMappings(prev => prev.map(mapping =>
        mapping.id === mappingId
          ? { ...mapping, active: newActiveState }
          : mapping
      ))

      setDependencyModal(prev => ({ ...prev, isOpen: false }))
      showSuccess(
        `Status Mapping ${newActiveState ? 'Activated' : 'Deactivated'}`,
        `The status mapping has been ${newActiveState ? 'activated' : 'deactivated'} successfully.`
      )
    } catch (error) {
      console.error('Error updating mapping:', error)
      showError('Update Failed', 'Failed to update mapping status. Please try again.')
    }
  }

  // Handle edit
  const handleEdit = (mappingId: number) => {
    const mapping = mappings.find(m => m.id === mappingId)
    if (mapping) {
      setEditModal({
        isOpen: true,
        mapping
      })
    }
  }

  // Handle edit save
  const handleEditSave = async (formData: Record<string, any>) => {
    if (!editModal.mapping) return

    try {
      const updateData: any = {
        status_from: formData.status_from,
        status_to: formData.status_to,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null,
        active: formData.active,
        apply_to_existing_statuses: formData.apply_to_existing_statuses || false
      }

      // Handle category - convert category name to category_id
      if (formData.category) {
        const category = categories.find(c => c.name === formData.category)
        if (category) {
          updateData.category_id = category.id
        }
      } else {
        // Empty string means clear the category
        updateData.category_id = null
      }

      const response = await statusesApi.updateStatusMapping(editModal.mapping.id, updateData)

      // Get integration info from the frontend state (already loaded)
      const selectedIntegration = integrations.find(i => i.id === updateData.integration_id)

      // Update local state with response data plus integration info from frontend
      const updatedMapping = {
        ...(response.data || response),
        integration_name: selectedIntegration?.name || null,
        integration_logo: selectedIntegration?.logo_filename || null
      }

      setMappings(prev => prev.map(m =>
        m.id === editModal.mapping!.id
          ? updatedMapping
          : m
      ))

      showSuccess('Mapping Updated', 'The status mapping has been updated successfully.')
      setEditModal({ isOpen: false, mapping: null })
    } catch (error) {
      console.error('Error updating mapping:', error)
      showError('Update Failed', 'Failed to update status mapping. Please try again.')
    }
  }

  // Handle create save
  const handleCreateSave = async (formData: Record<string, any>) => {
    try {
      // Find the category ID from the category name
      const category = categories.find(c => c.name === formData.status_category)
      if (!category) {
        showError('Invalid Category', 'Please select a valid status category.')
        return
      }

      const createData = {
        status_from: formData.status_from,
        status_to: formData.status_to,
        category_id: category.id,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null,
        apply_to_existing_statuses: formData.apply_to_existing_statuses || false
      }

      const response = await statusesApi.createStatusMapping(createData)

      // Get integration info from the frontend state (already loaded)
      const selectedIntegration = integrations.find(i => i.id === createData.integration_id)

      // Add new mapping to local state with integration info from frontend
      const newMapping = {
        ...(response.data || response),
        integration_name: selectedIntegration?.name || null,
        integration_logo: selectedIntegration?.logo_filename || null
      }

      setMappings(prev => [...prev, newMapping])

      showSuccess('Mapping Created', 'The status mapping has been created successfully.')
      setCreateModal({ isOpen: false })
    } catch (error) {
      console.error('Error creating mapping:', error)
      showError('Create Failed', 'Failed to create status mapping. Please try again.')
    }
  }

  // Handle delete
  const handleDelete = async (mappingId: number) => {
    const mapping = mappings.find(m => m.id === mappingId)
    if (!mapping) return

    confirmDelete(
      mapping.status_to,
      async () => {
        try {
          const response = await statusesApi.deleteStatusMapping(mappingId)

          // Remove from local state
          setMappings(prev => prev.filter(m => m.id !== mappingId))

          // Show success message from backend
          const message = response.data?.message || 'Status mapping deleted successfully.'
          showSuccess('Mapping Deleted', message)
        } catch (error) {
          console.error('Error deleting mapping:', error)
          showError('Delete Failed', 'Failed to delete status mapping. Please try again.')
        }
      }
    )
  }

  // Handle select all
  const handleSelectAll = () => {
    if (selectedIds.size === sortedMappings.length) {
      // Deselect all
      setSelectedIds(new Set())
    } else {
      // Select all visible mappings
      setSelectedIds(new Set(sortedMappings.map(m => m.id)))
    }
  }

  // Handle individual selection
  const handleSelectOne = (mappingId: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(mappingId)) {
      newSelected.delete(mappingId)
    } else {
      newSelected.add(mappingId)
    }
    setSelectedIds(newSelected)
  }

  // Handle remap all statuses
  const handleRemapAllStatuses = async () => {
    try {
      const response = await statusesApi.remapAllStatuses()
      const data = response.data

      showSuccess(
        'Remap Complete',
        `Scanned ${data.total_statuses_scanned} statuses, found ${data.mappings_applied} with mappings, updated ${data.statuses_updated} statuses`
      )
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to remap statuses'
      showError('Remap Failed', errorMessage)
    }
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return

    confirmDelete(
      `${selectedIds.size} status mapping${selectedIds.size > 1 ? 's' : ''}`,
      async () => {
        try {
          const mappingIds = Array.from(selectedIds)
          await statusesApi.bulkDeleteStatusMappings(mappingIds)

          // Remove from local state
          setMappings(prev => prev.filter(m => !selectedIds.has(m.id)))
          setSelectedIds(new Set())

          showSuccess(
            'Mappings Deleted',
            `Successfully deleted ${mappingIds.length} status mapping${mappingIds.length > 1 ? 's' : ''}.`
          )
        } catch (error) {
          console.error('Error bulk deleting mappings:', error)
          showError('Bulk Delete Failed', 'Failed to delete status mappings. Please try again.')
        }
      }
    )
  }

  // Handle bulk edit save
  const handleBulkEditSave = async (formData: Record<string, any>) => {
    try {
      const updateData: any = {}

      // Handle Status To field
      if (formData.status_to) {
        if (formData.status_to === '__CLEAR__') {
          // Special value to clear the status_to (set to empty string)
          updateData.status_to = ''
        } else {
          updateData.status_to = formData.status_to
        }
      }

      // Handle Status Category field
      if (formData.status_category) {
        if (formData.status_category === '__CLEAR__') {
          // Special value to clear the category
          updateData.category_id = null
        } else {
          // Find the category ID from the category name
          const category = categories.find(c => c.name === formData.status_category)
          if (category) {
            updateData.category_id = category.id
          }
        }
      }

      // Handle Integration field
      if (formData.integration_id) {
        if (formData.integration_id === '__CLEAR__') {
          // Special value to clear the integration
          updateData.integration_id = null
        } else {
          updateData.integration_id = parseInt(formData.integration_id)
        }
      }

      // Handle Active field
      if (formData.active) {
        updateData.active = formData.active === 'true'
      }

      // Handle Apply to Existing field
      if (formData.apply_to_existing_statuses) {
        updateData.apply_to_existing_statuses = formData.apply_to_existing_statuses
      }

      // Don't proceed if no fields to update
      if (Object.keys(updateData).length === 0) {
        showError('No Changes', 'Please select at least one field to update.')
        return
      }

      // Use bulk update endpoint for better performance (single transaction)
      const mappingIds = Array.from(selectedIds)
      const response = await statusesApi.bulkUpdateStatusMappings(mappingIds, updateData)
      const updatedMappings = response.data || response

      // Update local state with API response data
      setMappings(prev => prev.map(m => {
        // Find the updated mapping in the response
        const updated = updatedMappings.find((um: any) => um.id === m.id)
        if (updated) {
          return {
            ...m,
            ...updated
          }
        }
        return m
      }))

      showSuccess('Bulk Update Complete', `Successfully updated ${selectedIds.size} status mapping(s).`)
      setBulkEditModal({ isOpen: false })
      setSelectedIds(new Set())
    } catch (error) {
      console.error('Error bulk updating mappings:', error)
      showError('Bulk Update Failed', 'Failed to update status mappings. Please try again.')
    }
  }

  // Filtered mappings based on filter states
  const filteredMappings = mappings.filter(mapping => {
    const matchesStatusFrom = !statusFromFilter ||
      mapping.status_from.toLowerCase().includes(statusFromFilter.toLowerCase())
    const matchesStatusTo = !statusToFilter ||
      mapping.status_to.toLowerCase().includes(statusToFilter.toLowerCase())
    const matchesCategory = !categoryFilter ||
      (mapping.category && mapping.category.toLowerCase().includes(categoryFilter.toLowerCase()))
    const matchesIntegration = !integrationFilter ||
      (mapping.integration_name && mapping.integration_name.toLowerCase().includes(integrationFilter.toLowerCase()))
    const matchesStatus = !statusFilter ||
      (statusFilter === 'active' && mapping.active) ||
      (statusFilter === 'inactive' && !mapping.active)

    return matchesStatusFrom && matchesStatusTo && matchesCategory && matchesIntegration && matchesStatus
  })

  // Sort the filtered mappings
  const sortedMappings = [...filteredMappings].sort((a, b) => {
    if (!sortField) return 0

    let aVal: any = a[sortField as keyof StatusMapping]
    let bVal: any = b[sortField as keyof StatusMapping]

    // Handle null/undefined
    if (aVal == null && bVal == null) return 0
    if (aVal == null) return 1
    if (bVal == null) return -1

    // Convert to lowercase for string comparison
    if (typeof aVal === 'string') aVal = aVal.toLowerCase()
    if (typeof bVal === 'string') bVal = bVal.toLowerCase()

    // Compare
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  // Load integrations data
  const loadIntegrations = async () => {
    try {
      const response = await integrationsApi.getIntegrations()
      // Filter to only show data-type integrations (not AI providers) - case insensitive
      const dataIntegrations = response.data.filter((integration: Integration) =>
        integration.integration_type?.toLowerCase() === 'data' && integration.active
      )
      setIntegrations(dataIntegrations)
    } catch (err) {
      console.error('Error fetching integrations:', err)
      // Set fallback integrations if API fails
      setIntegrations([])
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Load mappings, integrations, and categories in parallel
        await Promise.all([
          (async () => {
            const response = await statusesApi.getStatusMappings()
            setMappings(response.data)
          })(),
          loadIntegrations(),
          (async () => {
            const response = await statusesApi.getStatusCategories()
            setCategories(response.data)
          })()
        ])
        setError(null)
      } catch (err) {
        console.error('Error fetching data:', err)
        setError('Failed to load status mappings')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const content = (
    <>
            {/* Content */}
            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-primary" />
                <h2 className="text-2xl font-semibold text-primary mb-2">
                  Loading...
                </h2>
                <p className="text-secondary">
                  Fetching status mappings
                </p>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">❌</div>
                <h2 className="text-2xl font-semibold text-primary mb-2">
                  Error
                </h2>
                <p className="text-secondary mb-6">
                  {error}
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-accent text-on-accent rounded-lg hover:bg-accent/90 transition-colors"
                >
                  Retry
                </button>
              </div>
            ) : (
              <>
                  {/* Filters Section */}
                  <div className="mb-6 p-6 rounded-lg shadow-md border border-gray-400"
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-1)'
                      e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = '#9ca3af'
                      e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                    }}
                  >
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                      {/* Status From Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Status From</label>
                        <input
                          type="text"
                          placeholder="Filter by status from..."
                          value={statusFromFilter}
                          onChange={(e) => setStatusFromFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Status To Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Status To</label>
                        <input
                          type="text"
                          placeholder="Filter by status to..."
                          value={statusToFilter}
                          onChange={(e) => setStatusToFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Category Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Category</label>
                        <select
                          value={categoryFilter}
                          onChange={(e) => setCategoryFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Categories</option>
                          <option value="To Do">To Do</option>
                          <option value="In Progress">In Progress</option>
                          <option value="Waiting">Waiting</option>
                          <option value="Done">Done</option>
                          <option value="Discarded">Discarded</option>
                        </select>
                      </div>

                      {/* Integration Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Integration</label>
                        <select
                          value={integrationFilter}
                          onChange={(e) => setIntegrationFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Integrations</option>
                          <option value="GitHub">GitHub</option>
                          <option value="Jira">Jira</option>
                        </select>
                      </div>

                      {/* Active Status Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Active Status</label>
                        <select
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Statuses</option>
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Status Mappings Table */}
                  <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
                    {/* Sticky Header Section */}
                    <div className="sticky top-16 z-20">
                      <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
                        <div className="flex items-center space-x-4">
                          <h2 className="text-lg font-semibold text-table-header">Status Mappings</h2>
                          {selectedIds.size > 0 && (
                            <span className="text-sm text-white/70">
                              ({selectedIds.size} selected)
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-3">
                          <button
                            onClick={() => setBulkEditModal({ isOpen: true })}
                            className={`px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2 ${selectedIds.size === 0 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                            <span className="text-sm font-medium text-primary">Bulk Edit</span>
                          </button>
                          <button
                            onClick={handleBulkDelete}
                            className={`px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2 ${selectedIds.size === 0 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                              <path d="M3 6h18"></path>
                              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                            </svg>
                            <span className="text-sm font-medium text-primary">Bulk Delete</span>
                          </button>
                          <button
                            onClick={handleRemapAllStatuses}
                            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
                            title="Scan all statuses and update their names based on current mappings"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                              <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
                              <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
                              <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
                              <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
                            </svg>
                            <span className="text-sm font-medium text-primary">Remap All</span>
                          </button>
                          <button
                            onClick={() => {
                              if (integrations.length === 0) {
                                showError('No Integrations Available', 'Please configure at least one data integration before creating status mappings.')
                                return
                              }
                              setCreateModal({ isOpen: true })
                            }}
                            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                              <path d="M5 12h14"></path>
                              <path d="M12 5v14"></path>
                            </svg>
                            <span className="text-sm font-medium text-primary">Create Mapping</span>
                          </button>
                        </div>
                      </div>

                      <div className="overflow-x-auto bg-table-column-header">
                        <table className="w-full" style={{ tableLayout: 'fixed' }}>
                          <colgroup>
                            <col style={{ width: '5%' }} />
                            <col style={{ width: '22%' }} />
                            <col style={{ width: '22%' }} />
                            <col style={{ width: '18%' }} />
                            <col style={{ width: '15%' }} />
                            <col style={{ width: '10%' }} />
                            <col style={{ width: '8%' }} />
                          </colgroup>
                          <thead className="bg-table-column-header">
                            <tr className="bg-table-column-header">
                              <th className="px-3 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                                <input
                                  type="checkbox"
                                  checked={sortedMappings.length > 0 && selectedIds.size === sortedMappings.length}
                                  onChange={handleSelectAll}
                                  className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                                  style={{ accentColor: 'var(--color-1)' }}
                                  title="Select all"
                                />
                              </th>
                              <th
                                className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                                onClick={() => handleSort('status_from')}
                              >
                                <div className="flex items-center gap-2">
                                  Status From
                                  {sortField === 'status_from' ? (
                                    sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                  ) : (
                                    <ArrowUpDown className="h-4 w-4 opacity-50" />
                                  )}
                                </div>
                              </th>
                              <th
                                className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                                onClick={() => handleSort('status_to')}
                              >
                                <div className="flex items-center gap-2">
                                  Status To
                                  {sortField === 'status_to' ? (
                                    sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                  ) : (
                                    <ArrowUpDown className="h-4 w-4 opacity-50" />
                                  )}
                                </div>
                              </th>
                              <th
                                className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                                onClick={() => handleSort('category')}
                              >
                                <div className="flex items-center justify-center gap-2">
                                  Category
                                  {sortField === 'category' ? (
                                    sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                  ) : (
                                    <ArrowUpDown className="h-4 w-4 opacity-50" />
                                  )}
                                </div>
                              </th>
                              <th
                                className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                                onClick={() => handleSort('integration_name')}
                              >
                                <div className="flex items-center justify-center gap-2">
                                  Integration
                                  {sortField === 'integration_name' ? (
                                    sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                  ) : (
                                    <ArrowUpDown className="h-4 w-4 opacity-50" />
                                  )}
                                </div>
                              </th>
                              <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Active</th>
                              <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Actions</th>
                            </tr>
                          </thead>
                        </table>
                      </div>
                    </div>
                    {/* End Sticky Header Section */}

                    {/* Scrollable Table Body */}
                    <div className="overflow-x-auto">
                      <table className="w-full" style={{ tableLayout: 'fixed' }}>
                        <colgroup>
                          <col style={{ width: '5%' }} />
                          <col style={{ width: '22%' }} />
                          <col style={{ width: '22%' }} />
                          <col style={{ width: '18%' }} />
                          <col style={{ width: '15%' }} />
                          <col style={{ width: '10%' }} />
                          <col style={{ width: '8%' }} />
                        </colgroup>
                        <tbody>
                            {sortedMappings.length === 0 ? (
                              <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                                <td colSpan={7} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                                  <div className="text-6xl mb-4">⚡</div>
                                  <p className="text-lg mb-2">No status mappings found</p>
                                  <p className="text-sm">Try adjusting your filters or create a new status mapping</p>
                                </td>
                              </tr>
                            ) : (
                              sortedMappings.map((mapping, index) => (
                                <tr
                                  key={mapping.id}
                                  className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!mapping.active ? 'opacity-50' : ''}`}
                                >
                                <td className="px-3 py-5 whitespace-nowrap text-center w-12">
                                  <input
                                    type="checkbox"
                                    checked={selectedIds.has(mapping.id)}
                                    onChange={() => handleSelectOne(mapping.id)}
                                    className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                                    style={{ accentColor: 'var(--color-1)' }}
                                  />
                                </td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{mapping.status_from}</td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{mapping.status_to}</td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">{mapping.category || '-'}</td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="flex items-center justify-center">
                                  <IntegrationLogo
                                    logoFilename={mapping.integration_logo}
                                    integrationName={mapping.integration_name}
                                  />
                                  {!mapping.integration_logo && (
                                    <span className="text-sm text-table-row">
                                      {mapping.integration_name || '-'}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div
                                  className="job-toggle-switch cursor-pointer"
                                  onClick={() => handleToggleActive(mapping.id, mapping.active)}
                                >
                                  <div className={`toggle-switch ${mapping.active ? 'active' : ''}`}>
                                    <div className="toggle-slider"></div>
                                  </div>
                                  <span className="toggle-label">{mapping.active ? 'On' : 'Off'}</span>
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="flex items-center justify-center space-x-2">
                                  <button
                                    onClick={() => handleEdit(mapping.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                                    title="Edit"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                    </svg>
                                  </button>
                                  <button
                                    onClick={() => handleDelete(mapping.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-red-500 shadow-sm hover:shadow-md transition-all"
                                    title="Delete"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M10 11v6"></path>
                                      <path d="M14 11v6"></path>
                                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                                      <path d="M3 6h18"></path>
                                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    </svg>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                          )}
                        </tbody>
                      </table>
                    </div>
                    {/* End Scrollable Table Body */}
                  </div>
              </>
            )}

      {/* Dependency Modal */}
      <DependencyModal
        isOpen={dependencyModal.isOpen}
        onClose={() => setDependencyModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={(_targetId) => performToggle(dependencyModal.mappingId!, dependencyModal.action === 'activate')}
        title={`${dependencyModal.action === 'deactivate' ? 'Deactivate' : 'Activate'} Status Mapping`}
        itemName={dependencyModal.mappingName}
        action={dependencyModal.action}
        dependencyCount={dependencyModal.dependencies.length}
        affectedItemsCount={dependencyModal.dependencies.reduce((sum: number, dep: any) => sum + (dep.affected_items_count || 0), 0)}
        dependencyType="status mapping(s)"
        affectedItemType="work item(s)"
        reassignmentTargets={dependencyModal.reassignmentTargets}
        targetDisplayField="status_to"
        allowSkipReassignment={dependencyModal.action === 'deactivate'}
        onShowError={showError}
      />

      {/* Edit Modal */}
      {editModal.mapping && (
        <EditModal
          isOpen={editModal.isOpen}
          onClose={() => setEditModal({ isOpen: false, mapping: null })}
          onSave={handleEditSave}
          title="Edit Status Mapping"
          fields={[
            {
              name: 'status_from',
              label: 'Original Name',
              type: 'text',
              value: editModal.mapping.status_from,
              required: true,
              placeholder: 'Enter original status name'
            },
            {
              name: 'status_to',
              label: 'Mapped Name',
              type: 'text',
              value: editModal.mapping.status_to,
              required: true,
              placeholder: 'Enter mapped status name'
            },
            {
              name: 'category',
              label: 'Status Category',
              type: 'select',
              value: editModal.mapping.category || '',
              required: false,
              options: [
                { value: '', label: '- No Category -' },
                { value: 'To Do', label: 'To Do' },
                { value: 'In Progress', label: 'In Progress' },
                { value: 'Waiting', label: 'Waiting' },
                { value: 'Done', label: 'Done' },
                { value: 'Discarded', label: 'Discarded' }
              ]
            },
            {
              name: 'integration_id',
              label: 'Integration',
              type: 'select',
              value: editModal.mapping.integration_id || '',
              required: false,  // ✅ Allow clearing integration
              options: integrations.map(integration => ({
                value: integration.id.toString(),
                label: integration.name
              })),
              customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
                // Use formData if it exists (even if empty string), otherwise fall back to field.value
                const selectedIntegrationId = field.name in formData ? formData[field.name] : field.value
                const selectedIntegration = selectedIntegrationId ? integrations.find(i => i.id.toString() === selectedIntegrationId.toString()) : null

                return (
                  <div className="space-y-3">
                    <select
                      id={field.name}
                      value={selectedIntegrationId || ''}
                      onChange={(e) => handleInputChange(field.name, e.target.value)}
                      className={`input w-full ${errors[field.name] ? 'border-red-500' : ''}`}
                    >
                      <option value="">- No Integration -</option>
                      {field.options?.map((option: any) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    {selectedIntegration && (
                      <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
                        {selectedIntegration.logo_filename ? (
                          <img
                            src={`/assets/integrations/${selectedIntegration.logo_filename}`}
                            alt={selectedIntegration.name}
                            className="h-8 w-8 object-contain"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                        ) : (
                          <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center">
                            <span className="text-sm text-blue-600 font-semibold">
                              {selectedIntegration.name.charAt(0)}
                            </span>
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{selectedIntegration.name}</p>
                          <p className="text-xs text-gray-500">Integration Provider</p>
                        </div>
                      </div>
                    )}
                  </div>
                )
              }
            },
            {
              name: 'active',
              label: '',
              type: 'text',
              value: editModal.mapping.active,
              required: false,
              customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
                return (
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-secondary whitespace-nowrap w-24">
                      Active
                    </label>
                    <div
                      className="job-toggle-switch cursor-pointer"
                      onClick={() => handleInputChange('active', !formData.active)}
                    >
                      <div className={`toggle-switch ${formData.active ? 'active' : ''}`}>
                        <div className="toggle-slider"></div>
                      </div>
                      <span className="toggle-label">{formData.active ? 'On' : 'Off'}</span>
                    </div>
                  </div>
                )
              }
            },
            {
              name: 'apply_to_existing_statuses',
              label: 'Apply to Existing Statuses',
              type: 'text',  // Use 'text' to prevent default checkbox rendering since we have customRender
              required: false,
              value: false,
              placeholder: 'Update existing statuses with matching original names to use this mapping',
              customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
                // Check if status_from or status_to has changed
                const statusFromChanged = formData.status_from !== editModal.mapping?.status_from
                const statusToChanged = formData.status_to !== editModal.mapping?.status_to
                const isEnabled = statusFromChanged || statusToChanged

                return (
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        id={field.name}
                        checked={formData[field.name] || false}
                        onChange={(e) => handleInputChange(field.name, e.target.checked)}
                        disabled={!isEnabled}
                        className="w-4 h-4 bg-secondary border-gray-400 rounded focus:ring-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                          accentColor: 'var(--color-1)'
                        }}
                      />
                      <label
                        htmlFor={field.name}
                        className={`text-sm font-medium ${isEnabled ? 'text-secondary' : 'text-gray-400'}`}
                      >
                        {field.label}
                      </label>
                    </div>
                    {field.placeholder && (
                      <p className={`text-xs ml-7 ${isEnabled ? 'text-gray-500' : 'text-gray-400'}`}>
                        {isEnabled
                          ? field.placeholder
                          : 'This option is only available when Original Name or Mapped Name is changed'}
                      </p>
                    )}
                  </div>
                )
              }
            }
          ]}
        />
      )}

      {/* Create Modal */}
      <CreateModal
        isOpen={createModal.isOpen}
        onClose={() => setCreateModal({ isOpen: false })}
        onSave={handleCreateSave}
        title="Create Status Mapping"
        fields={[
          {
            name: 'status_from',
            label: 'Original Name',
            type: 'text',
            required: true,
            placeholder: 'Enter original status name'
          },
          {
            name: 'status_to',
            label: 'Mapped Name',
            type: 'text',
            required: true,
            placeholder: 'Enter mapped status name'
          },
          {
            name: 'status_category',
            label: 'Status Category',
            type: 'select',
            required: true,
            defaultValue: 'To Do',
            options: [
              { value: 'To Do', label: 'To Do' },
              { value: 'In Progress', label: 'In Progress' },
              { value: 'Waiting', label: 'Waiting' },
              { value: 'Done', label: 'Done' },
              { value: 'Discarded', label: 'Discarded' }
            ]
          },
          {
            name: 'integration_id',
            label: 'Integration',
            type: 'select',
            required: true,
            defaultValue: integrations.length > 0 ? integrations[0].id.toString() : '',
            options: integrations.map(integration => ({
              value: integration.id.toString(),
              label: integration.name
            })),
            customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
              const selectedIntegrationId = formData[field.name] || field.defaultValue
              const selectedIntegration = integrations.find(i => i.id.toString() === selectedIntegrationId)

              return (
                <div className="space-y-3">
                  <select
                    id={field.name}
                    value={formData[field.name] || ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    className={`input w-full ${errors[field.name] ? 'border-red-500' : ''}`}
                  >
                    {field.options?.map((option: any) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {selectedIntegration && (
                    <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
                      {selectedIntegration.logo_filename ? (
                        <img
                          src={`/assets/integrations/${selectedIntegration.logo_filename}`}
                          alt={selectedIntegration.name}
                          className="h-8 w-8 object-contain"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                      ) : (
                        <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center">
                          <span className="text-sm text-blue-600 font-semibold">
                            {selectedIntegration.name.charAt(0)}
                          </span>
                        </div>
                      )}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{selectedIntegration.name}</p>
                        <p className="text-xs text-gray-500">Integration Provider</p>
                      </div>
                    </div>
                  )}
                </div>
              )
            }
          },
          {
            name: 'apply_to_existing_statuses',
            label: 'Apply to Existing Statuses',
            type: 'checkbox',
            required: false,
            defaultValue: false,
            placeholder: 'Update existing statuses with matching original names to use this mapping'
          }
        ]}
      />

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={bulkEditModal.isOpen}
        onClose={() => setBulkEditModal({ isOpen: false })}
        onSave={handleBulkEditSave}
        title="Bulk Edit Status Mappings"
        selectedCount={selectedIds.size}
        fields={[
          {
            name: 'status_to',
            label: 'Mapped Name',
            type: 'text',
            placeholder: 'Enter new mapped name (leave empty for no change)',
            customRender: (field: any, formData: any, handleInputChange: any) => {
              return (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      id={field.name}
                      value={formData[field.name] === '__CLEAR__' ? '' : (formData[field.name] || '')}
                      onChange={(e) => handleInputChange(field.name, e.target.value)}
                      placeholder={field.placeholder}
                      className="input flex-1"
                      disabled={formData[field.name] === '__CLEAR__'}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (formData[field.name] === '__CLEAR__') {
                          handleInputChange(field.name, '')
                        } else {
                          handleInputChange(field.name, '__CLEAR__')
                        }
                      }}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        formData[field.name] === '__CLEAR__'
                          ? 'bg-red-600 text-white hover:bg-red-700'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                      title={formData[field.name] === '__CLEAR__' ? 'Cancel clear' : 'Clear status'}
                    >
                      {formData[field.name] === '__CLEAR__' ? '✓ Clearing' : '🗑️ Clear'}
                    </button>
                  </div>
                  {formData[field.name] === '__CLEAR__' && (
                    <p className="text-sm text-red-600">
                      ⚠️ This will clear the "Status To" field for all selected mappings
                    </p>
                  )}
                </div>
              )
            }
          },
          {
            name: 'status_category',
            label: 'Status Category',
            type: 'select',
            options: [
              { value: '__CLEAR__', label: '🗑️ Clear Category' },
              ...categories.map(category => ({
                value: category.name,
                label: category.name
              }))
            ]
          },
          {
            name: 'integration_id',
            label: 'Integration',
            type: 'select',
            options: [
              { value: '__CLEAR__', label: '🗑️ Clear Integration' },
              ...integrations.map(integration => ({
                value: integration.id.toString(),
                label: integration.name
              }))
            ],
            customRender: (field: any, formData: any, handleInputChange: any) => {
              const selectedIntegrationId = formData['integration_id']
              const selectedIntegration = integrations.find(i => i.id.toString() === selectedIntegrationId)

              const integrationOptions = [
                { value: '__CLEAR__', label: '🗑️ Clear Integration' },
                ...integrations.map(integration => ({
                  value: integration.id.toString(),
                  label: integration.name
                }))
              ]

              return (
                <div className="space-y-3">
                  <select
                    id="integration_id"
                    value={formData['integration_id'] || ''}
                    onChange={(e) => handleInputChange('integration_id', e.target.value)}
                    className="input w-full"
                  >
                    <option value="">Select integration</option>
                    {integrationOptions.map((option: any) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {selectedIntegration && selectedIntegrationId !== '__CLEAR__' && (
                    <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
                      {selectedIntegration.logo_filename ? (
                        <img
                          src={`/assets/integrations/${selectedIntegration.logo_filename}`}
                          alt={selectedIntegration.name}
                          className="h-8 w-8 object-contain"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                      ) : (
                        <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center">
                          <span className="text-sm text-blue-600 font-semibold">
                            {selectedIntegration.name.charAt(0)}
                          </span>
                        </div>
                      )}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{selectedIntegration.name}</p>
                        <p className="text-xs text-gray-500">Integration Provider</p>
                      </div>
                    </div>
                  )}
                </div>
              )
            }
          },
          {
            name: 'active',
            label: 'Active Status',
            type: 'select',
            placeholder: 'Select active status',
            options: [
              { value: 'true', label: '✓ Activate' },
              { value: 'false', label: '✗ Deactivate' }
            ]
          },
          {
            name: 'apply_to_existing_statuses',
            label: 'Apply to Existing Statuses',
            type: 'text',
            customRender: (field: any, formData: any, handleInputChange: any) => {
              // Only show if mapped name or category is being changed
              const hasRelevantChanges = formData.status_to || formData.status_category

              if (!hasRelevantChanges) {
                return null
              }

              return (
                <div className="space-y-2">
                  <label className="flex items-center space-x-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={formData.apply_to_existing_statuses || false}
                      onChange={(e) => handleInputChange('apply_to_existing_statuses', e.target.checked)}
                      className="w-5 h-5 rounded border-2 border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer transition-all"
                      style={{ accentColor: 'var(--color-1)' }}
                    />
                    <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition-colors">
                      Update existing statuses with matching original names
                    </span>
                  </label>
                  <p className="text-xs text-gray-500 ml-8">
                    When enabled, all existing statuses with matching original names will be updated to use the new mapped name and/or category
                  </p>
                </div>
              )
            },
            placeholder: 'Update existing statuses with matching original names to use this mapping'
          }
        ]}
      />

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmation.isOpen}
        onClose={hideConfirmation}
        onConfirm={confirmation.onConfirm}
        title={confirmation.title}
        message={confirmation.message}
        confirmText={confirmation.confirmText}
        cancelText={confirmation.cancelText}
        type={confirmation.type}
        icon={confirmation.icon}
      />

      {/* Toast Notifications - Always show, even in embedded mode */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

      {/* Back to Top Button - Always show, even in embedded mode */}
      <BackToTop />
    </>
  )

  if (embedded) {
    return content
  }

  return (
    <div className="min-h-screen">
      <Header />
      <div className="flex">
        <CollapsedSidebar />
        <main className="flex-1 ml-16 py-8">
          <div className="ml-12 mr-12">
            {content}
          </div>
        </main>
      </div>
    </div>
  )
}

export default StatusesMappingsPage
