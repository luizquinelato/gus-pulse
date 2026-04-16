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
import { witsApi, integrationsApi } from '../services/etlApiService'

interface WitMapping {
  id: number
  wit_from: string
  wit_to: string
  hierarchy_level?: number
  hierarchy_name?: string
  workflow_id?: number
  workflow_name?: string
  integration_id?: number
  integration_name?: string
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

interface WitHierarchy {
  id: number
  level: number
  name: string
  description?: string
  integration_id?: number
  integration_name?: string
  integration_logo?: string
  active: boolean
}

interface WitsMappingsPageProps {
  embedded?: boolean
}

const WitsMappingsPage: React.FC<WitsMappingsPageProps> = ({ embedded = false }) => {
  const [mappings, setMappings] = useState<WitMapping[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [hierarchies, setHierarchies] = useState<WitHierarchy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Filter states
  const [typeFilter, setTypeFilter] = useState('')
  const [hierarchyLevelFilter, setHierarchyLevelFilter] = useState('')
  const [integrationFilter, setIntegrationFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Sort states
  const [sortField, setSortField] = useState<string | null>(null)
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

  // Helper function to get hierarchy info by level
  const getHierarchyByLevel = (level: number | undefined) => {
    if (level === undefined || level === null) return null
    return hierarchies.find(h => h.level === level)
  }

  // Edit modal state
  const [editModal, setEditModal] = useState({
    isOpen: false,
    mapping: null as WitMapping | null
  })

  // Create modal state
  const [createModal, setCreateModal] = useState({
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

  // Bulk edit modal state
  const [bulkEditModal, setBulkEditModal] = useState({
    isOpen: false
  })

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Handler functions
  const checkDependencies = async (mappingId: number): Promise<any> => {
    try {
      // TODO: Implement actual dependency checking API call
      // For now, return mock data
      return {
        has_dependencies: Math.random() > 0.7, // 30% chance of having dependencies
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
            mappingName: mapping.wit_to,
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
        `Mapping ${newActiveState ? 'Activated' : 'Deactivated'}`,
        `The mapping has been ${newActiveState ? 'activated' : 'deactivated'} successfully.`
      )
    } catch (error) {
      console.error('Error updating mapping:', error)
      showError('Update Failed', 'Failed to update mapping status. Please try again.')
    }
  }

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
      const updateData = {
        wit_from: formData.wit_from,
        wit_to: formData.wit_to,
        hierarchy_level: parseInt(formData.hierarchy_level),
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null,
        active: formData.active,
        apply_to_existing_wits: formData.apply_to_existing_wits || false
      }

      const response = await witsApi.updateWitMapping(editModal.mapping.id, updateData)

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

      showSuccess('Mapping Updated', 'The mapping has been updated successfully.')
      setEditModal({ isOpen: false, mapping: null })
    } catch (error) {
      console.error('Error updating mapping:', error)
      showError('Update Failed', 'Failed to update mapping. Please try again.')
    }
  }

  const handleDelete = async (mappingId: number) => {
    const mapping = mappings.find(m => m.id === mappingId)
    if (!mapping) return

    confirmDelete(
      mapping.wit_to,
      async () => {
        try {
          const response = await witsApi.deleteWitMapping(mappingId)

          // Remove from local state
          setMappings(prev => prev.filter(m => m.id !== mappingId))

          // Show success message from backend
          const message = response.data?.message || 'Mapping deleted successfully.'
          showSuccess('Mapping Deleted', message)
        } catch (error) {
          console.error('Error deleting mapping:', error)
          showError('Delete Failed', 'Failed to delete mapping. Please try again.')
        }
      }
    )
  }

  const handleCreateMapping = () => {
    if (integrations.length === 0) {
      showError('No Integrations Available', 'Please configure at least one data integration before creating mappings.')
      return
    }
    setCreateModal({ isOpen: true })
  }

  // Handle remap all WITs
  const handleRemapAllWits = async () => {
    try {
      const response = await witsApi.remapAllWits()
      const data = response.data

      showSuccess(
        'Remap Complete',
        `Scanned ${data.total_wits_scanned} WITs, found ${data.mappings_applied} with mappings, updated ${data.wits_updated} WITs`
      )
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to remap WITs'
      showError('Remap Failed', errorMessage)
    }
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return

    confirmDelete(
      `${selectedIds.size} WIT mapping${selectedIds.size > 1 ? 's' : ''}`,
      async () => {
        try {
          const mappingIds = Array.from(selectedIds)
          await witsApi.bulkDeleteWitMappings(mappingIds)

          // Remove from local state
          setMappings(prev => prev.filter(m => !selectedIds.has(m.id)))
          setSelectedIds(new Set())

          showSuccess(
            'Mappings Deleted',
            `Successfully deleted ${mappingIds.length} WIT mapping${mappingIds.length > 1 ? 's' : ''}.`
          )
        } catch (error) {
          console.error('Error bulk deleting mappings:', error)
          showError('Bulk Delete Failed', 'Failed to delete WIT mappings. Please try again.')
        }
      }
    )
  }

  // Handle bulk edit save
  const handleBulkEditSave = async (formData: Record<string, any>) => {
    try {
      const updateData: any = {}

      // Handle WIT To field
      if (formData.wit_to) {
        updateData.wit_to = formData.wit_to
      }

      // Handle Hierarchy Level field
      if (formData.hierarchy_level) {
        if (formData.hierarchy_level === '__CLEAR__') {
          // Special value to clear the hierarchy level
          updateData.hierarchy_level = null
        } else {
          updateData.hierarchy_level = parseInt(formData.hierarchy_level)
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
      if (formData.apply_to_existing_wits) {
        updateData.apply_to_existing_wits = formData.apply_to_existing_wits
      }

      // Use bulk update endpoint for better performance (single transaction)
      const mappingIds = Array.from(selectedIds)
      const response = await witsApi.bulkUpdateWitMappings(mappingIds, updateData)
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

      // Clear selection and close modal
      setSelectedIds(new Set())
      setBulkEditModal({ isOpen: false })

      showSuccess(
        'Bulk Edit Complete',
        `Successfully updated ${mappingIds.length} WIT mapping${mappingIds.length > 1 ? 's' : ''}.`
      )
    } catch (error) {
      console.error('Error bulk editing mappings:', error)
      showError('Bulk Edit Failed', 'Failed to update WIT mappings. Please try again.')
    }
  }

  // Handle create save
  const handleCreateSave = async (formData: Record<string, any>) => {
    try {
      const createData = {
        wit_from: formData.wit_from,
        wit_to: formData.wit_to,
        hierarchy_level: parseInt(formData.hierarchy_level),
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null,
        apply_to_existing_wits: formData.apply_to_existing_wits || false
      }

      const response = await witsApi.createWitMapping(createData)

      // Get integration info from the frontend state (already loaded)
      const selectedIntegration = integrations.find(i => i.id === createData.integration_id)

      // Add new mapping to local state with integration info from frontend
      const newMapping = {
        ...(response.data || response),
        integration_name: selectedIntegration?.name || null,
        integration_logo: selectedIntegration?.logo_filename || null
      }

      setMappings(prev => [...prev, newMapping])

      showSuccess('Mapping Created', 'The mapping has been created successfully.')
      setCreateModal({ isOpen: false })
    } catch (error) {
      console.error('Error creating mapping:', error)
      showError('Create Failed', 'Failed to create mapping. Please try again.')
    }
  }

  // Filtered mappings based on filter states
  const filteredMappings = mappings.filter(mapping => {
    const matchesType = !typeFilter ||
      mapping.wit_to.toLowerCase().includes(typeFilter.toLowerCase())
    const matchesHierarchyLevel = !hierarchyLevelFilter ||
      (mapping.hierarchy_level !== null && mapping.hierarchy_level !== undefined &&
       mapping.hierarchy_level.toString() === hierarchyLevelFilter)
    const matchesIntegration = !integrationFilter ||
      (mapping.integration_name && mapping.integration_name.toLowerCase().includes(integrationFilter.toLowerCase()))
    const matchesStatus = !statusFilter ||
      (statusFilter === 'active' && mapping.active) ||
      (statusFilter === 'inactive' && !mapping.active)

    return matchesType && matchesHierarchyLevel && matchesIntegration && matchesStatus
  })

  // Sort the filtered mappings
  const sortedMappings = [...filteredMappings].sort((a, b) => {
    if (!sortField) return 0

    let aVal: any = a[sortField as keyof WitMapping]
    let bVal: any = b[sortField as keyof WitMapping]

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

  // Load hierarchies data
  const loadHierarchies = async () => {
    try {
      const response = await witsApi.getWitsHierarchies()
      setHierarchies(response.data)
    } catch (err) {
      console.error('Error fetching hierarchies:', err)
      setHierarchies([])
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Load mappings, integrations, and hierarchies in parallel
        await Promise.all([
          (async () => {
            const response = await witsApi.getWitMappings()
            setMappings(response.data)
          })(),
          loadIntegrations(),
          loadHierarchies()
        ])
        setError(null)
      } catch (err) {
        console.error('Error fetching data:', err)
        setError('Failed to load work item type mappings')
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
                  Fetching work item type mappings
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
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {/* Type Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Work Item Type</label>
                        <input
                          type="text"
                          placeholder="Filter by type..."
                          value={typeFilter}
                          onChange={(e) => setTypeFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Hierarchy Level Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Hierarchy Level</label>
                        <select
                          value={hierarchyLevelFilter}
                          onChange={(e) => setHierarchyLevelFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Levels</option>
                          <option value="4">Level 4 (Capital Investment)</option>
                          <option value="3">Level 3 (Product Objective)</option>
                          <option value="2">Level 2 (Milestone)</option>
                          <option value="1">Level 1 (Epic)</option>
                          <option value="0">Level 0 (Story/Task/Bug)</option>
                          <option value="-1">Level -1 (Sub-task)</option>
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

                      {/* Status Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Status</label>
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

                  {/* Work Item Type Mappings Table */}
                  <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
                    {/* Sticky Header Section */}
                    <div className="sticky top-16 z-20 bg-table-container">
                      <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
                        <div className="flex items-center space-x-4">
                          <h2 className="text-lg font-semibold text-table-header">Work Item Type Mappings</h2>
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
                            onClick={handleRemapAllWits}
                            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
                            title="Scan all WITs and update their names based on current mappings"
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
                            onClick={handleCreateMapping}
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
                            <col style={{ width: '17%' }} />
                            <col style={{ width: '17%' }} />
                            <col style={{ width: '14%' }} />
                            <col style={{ width: '17%' }} />
                            <col style={{ width: '12%' }} />
                            <col style={{ width: '10%' }} />
                            <col style={{ width: '8%' }} />
                          </colgroup>
                          <thead className="bg-table-column-header">
                          <tr className="bg-table-column-header">
                            <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                              <input
                                type="checkbox"
                                checked={selectedIds.size === filteredMappings.length && filteredMappings.length > 0}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedIds(new Set(filteredMappings.map(m => m.id)))
                                  } else {
                                    setSelectedIds(new Set())
                                  }
                                }}
                                className="w-4 h-4 cursor-pointer"
                                style={{ accentColor: 'var(--color-1)' }}
                              />
                            </th>
                            <th
                              className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('wit_from')}
                            >
                              <div className="flex items-center gap-2">
                                Original Name
                                {sortField === 'wit_from' ? (
                                  sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </div>
                            </th>
                            <th
                              className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('wit_to')}
                            >
                              <div className="flex items-center gap-2">
                                Mapped Name
                                {sortField === 'wit_to' ? (
                                  sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </div>
                            </th>
                            <th
                              className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('hierarchy_level')}
                            >
                              <div className="flex items-center justify-center gap-2">
                                Hierarchy Level
                                {sortField === 'hierarchy_level' ? (
                                  sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </div>
                            </th>
                            <th
                              className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('workflow_name')}
                            >
                              <div className="flex items-center justify-center gap-2">
                                Workflow
                                {sortField === 'workflow_name' ? (
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

                    {/* Scrollable Body Section */}
                    <div className="overflow-x-auto">
                      <table className="w-full" style={{ tableLayout: 'fixed' }}>
                        <colgroup>
                          <col style={{ width: '5%' }} />
                          <col style={{ width: '17%' }} />
                          <col style={{ width: '17%' }} />
                          <col style={{ width: '14%' }} />
                          <col style={{ width: '17%' }} />
                          <col style={{ width: '12%' }} />
                          <col style={{ width: '10%' }} />
                          <col style={{ width: '8%' }} />
                        </colgroup>
                      <tbody>
                        {sortedMappings.length === 0 ? (
                          <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                            <td colSpan={8} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                              <div className="text-6xl mb-4">⚡</div>
                              <p className="text-lg mb-2">No mappings found</p>
                              <p className="text-sm">Try adjusting your filters or create a new mapping</p>
                            </td>
                          </tr>
                        ) : (
                          sortedMappings.map((mapping, index) => {
                            const hierarchy = getHierarchyByLevel(mapping.hierarchy_level)
                            return (
                              <tr
                                key={mapping.id}
                                className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!mapping.active ? 'opacity-50' : ''}`}
                              >
                                <td className="px-6 py-5 whitespace-nowrap text-center">
                                  <input
                                    type="checkbox"
                                    checked={selectedIds.has(mapping.id)}
                                    onChange={(e) => {
                                      const newSelected = new Set(selectedIds)
                                      if (e.target.checked) {
                                        newSelected.add(mapping.id)
                                      } else {
                                        newSelected.delete(mapping.id)
                                      }
                                      setSelectedIds(newSelected)
                                    }}
                                    className="w-4 h-4 cursor-pointer"
                                    style={{ accentColor: 'var(--color-1)' }}
                                  />
                                </td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{mapping.wit_from}</td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{mapping.wit_to}</td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">
                                  {hierarchy ? (
                                    <div className="flex flex-col items-center">
                                      <span className="font-semibold">{hierarchy.name}</span>
                                      <span className="text-xs text-secondary opacity-70">Level {hierarchy.level}</span>
                                    </div>
                                  ) : (
                                    <span>{mapping.hierarchy_level ?? '-'}</span>
                                  )}
                                </td>
                                <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">{mapping.workflow_name || '-'}</td>
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
                              <td className="px-6 py-5 whitespace-nowrap text-center text-sm font-medium">
                                <div className="flex justify-center space-x-2">
                                  <button
                                    onClick={() => handleEdit(mapping.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                                    aria-label="Edit mapping"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                    </svg>
                                  </button>
                                  <button
                                    onClick={() => handleDelete(mapping.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-red-500 shadow-sm hover:shadow-md transition-all"
                                    aria-label="Delete mapping"
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
                            )
                          })
                        )}
                      </tbody>
                      </table>
                    </div>
                  </div>
              </>
            )}

      {/* Dependency Modal */}
      <DependencyModal
        isOpen={dependencyModal.isOpen}
        onClose={() => setDependencyModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={(_targetId) => performToggle(dependencyModal.mappingId!, dependencyModal.action === 'activate')}
        title={`${dependencyModal.action === 'deactivate' ? 'Deactivate' : 'Activate'} WIT Mapping`}
        itemName={dependencyModal.mappingName}
        action={dependencyModal.action}
        dependencyCount={dependencyModal.dependencies.length}
        affectedItemsCount={dependencyModal.dependencies.reduce((sum: number, dep: any) => sum + (dep.affected_items_count || 0), 0)}
        dependencyType="work item(s)"
        affectedItemType="work item(s)"
        reassignmentTargets={dependencyModal.reassignmentTargets}
        targetDisplayField="wit_to"
        allowSkipReassignment={dependencyModal.action === 'deactivate'}
        onShowError={showError}
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

      {/* Edit Modal */}
      {editModal.mapping && (
        <EditModal
          isOpen={editModal.isOpen}
          onClose={() => setEditModal({ isOpen: false, mapping: null })}
          onSave={handleEditSave}
          title="Edit Mapping"
          fields={[
            {
              name: 'wit_from',
              label: 'Original Name',
              type: 'text',
              value: editModal.mapping.wit_from,
              required: true,
              placeholder: 'Enter original work item type name'
            },
            {
              name: 'wit_to',
              label: 'Mapped Name',
              type: 'text',
              value: editModal.mapping.wit_to,
              required: true,
              placeholder: 'Enter mapped work item type name'
            },
            {
              name: 'hierarchy_level',
              label: 'Hierarchy',
              type: 'select',
              value: editModal.mapping.hierarchy_level?.toString() || '',
              required: true,
              options: hierarchies
                .sort((a, b) => b.level - a.level) // Sort by level descending
                .map(hierarchy => ({
                  value: hierarchy.level.toString(),
                  label: `${hierarchy.name} (Level ${hierarchy.level})`
                }))
            },
            {
              name: 'integration_id',
              label: 'Integration',
              type: 'select',
              value: editModal.mapping.integration_id ? editModal.mapping.integration_id.toString() : '',  // ✅ Explicitly convert to string or empty
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
              name: 'apply_to_existing_wits',
              label: 'Apply to Existing WITs',
              type: 'text',  // Use 'text' to prevent default checkbox rendering since we have customRender
              value: false,
              required: false,
              customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
                // Check if wit_from or wit_to has changed
                const witFromChanged = formData.wit_from !== editModal.mapping.wit_from
                const witToChanged = formData.wit_to !== editModal.mapping.wit_to
                const hasChanges = witFromChanged || witToChanged

                return (
                  <div className="space-y-2">
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={formData.apply_to_existing_wits || false}
                        onChange={(e) => handleInputChange('apply_to_existing_wits', e.target.checked)}
                        disabled={!hasChanges}
                        className="w-4 h-4 bg-secondary border-gray-400 rounded focus:ring-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                          accentColor: 'var(--color-1)'
                        }}
                      />
                      <span className={`text-sm ${hasChanges ? 'text-primary' : 'text-secondary opacity-50'}`}>
                        Update existing WITs with matching original names to use this mapping
                      </span>
                    </label>
                    {!hasChanges && (
                      <p className="text-xs text-secondary ml-7">
                        This option is only available when Original Name or Mapped Name is changed
                      </p>
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
            }
          ]}
        />
      )}

      {/* Create Modal */}
      <CreateModal
        isOpen={createModal.isOpen}
        onClose={() => setCreateModal({ isOpen: false })}
        onSave={handleCreateSave}
        title="Create Mapping"
        fields={[
          {
            name: 'wit_from',
            label: 'Original Name',
            type: 'text',
            required: true,
            placeholder: 'Enter original work item type name'
          },
          {
            name: 'wit_to',
            label: 'Mapped Name',
            type: 'text',
            required: true,
            placeholder: 'Enter mapped work item type name'
          },
          {
            name: 'hierarchy_level',
            label: 'Hierarchy',
            type: 'select',
            required: true,
            defaultValue: hierarchies.length > 0 ? hierarchies[0].level.toString() : '',
            options: hierarchies
              .sort((a, b) => b.level - a.level) // Sort by level descending
              .map(hierarchy => ({
                value: hierarchy.level.toString(),
                label: `${hierarchy.name} (Level ${hierarchy.level})`
              }))
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
            name: 'apply_to_existing_wits',
            label: 'Apply to Existing WITs',
            type: 'checkbox',
            defaultValue: false,
            placeholder: 'Update existing WITs with matching original names to use this mapping'
          }
        ]}
      />

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={bulkEditModal.isOpen}
        onClose={() => setBulkEditModal({ isOpen: false })}
        onSave={handleBulkEditSave}
        title="Bulk Edit WIT Mappings"
        selectedCount={selectedIds.size}
        fields={[
          {
            name: 'wit_to',
            label: 'Mapped Name',
            type: 'text',
            placeholder: 'Enter new mapped name (leave empty for no change)'
          },
          {
            name: 'hierarchy_level',
            label: 'Hierarchy Level',
            type: 'select',
            placeholder: 'Select hierarchy level',
            options: [
              { value: '__CLEAR__', label: '🗑️ Clear Hierarchy Level' },
              ...hierarchies
                .sort((a, b) => b.level - a.level)
                .map(hierarchy => ({
                  value: hierarchy.level.toString(),
                  label: `${hierarchy.name} (Level ${hierarchy.level})`
                }))
            ]
          },
          {
            name: 'integration_id',
            label: 'Integration',
            type: 'select',
            placeholder: 'Select integration',
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
            name: 'apply_to_existing_wits',
            label: 'Apply to Existing WITs',
            type: 'text',
            customRender: (field: any, formData: any, handleInputChange: any) => {
              // Only show if mapped name or hierarchy level is being changed
              const hasRelevantChanges = formData.wit_to || formData.hierarchy_level

              if (!hasRelevantChanges) {
                return null
              }

              return (
                <div className="space-y-2">
                  <label className="flex items-center space-x-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={formData.apply_to_existing_wits || false}
                      onChange={(e) => handleInputChange('apply_to_existing_wits', e.target.checked)}
                      className="w-5 h-5 rounded border-2 border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer transition-all"
                      style={{ accentColor: 'var(--color-1)' }}
                    />
                    <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition-colors">
                      Update existing WITs with matching original names
                    </span>
                  </label>
                  <p className="text-xs text-gray-500 ml-8">
                    When enabled, all existing WITs with matching original names will be updated to use the new mapped name and/or hierarchy level
                  </p>
                </div>
              )
            },
            placeholder: 'Update existing WITs with matching original names to use this mapping'
          }
        ]}
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

export default WitsMappingsPage
