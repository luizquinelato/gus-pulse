import React, { useState, useEffect } from 'react'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import Header from '../components/Header'
import CollapsedSidebar from '../components/CollapsedSidebar'
import EditModal from '../components/EditModal'
import CreateModal from '../components/CreateModal'
import BulkEditModal from '../components/BulkEditModal'
import ConfirmationModal from '../components/ConfirmationModal'
import BackToTop from '../components/BackToTop'
import ToastContainer from '../components/ToastContainer'
import IntegrationLogo from '../components/IntegrationLogo'
import { useToast } from '../hooks/useToast'
import { useConfirmation } from '../hooks/useConfirmation'
import { witsApi, integrationsApi } from '../services/etlApiService'

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

interface Integration {
  id: number
  name: string
  integration_type: string
  logo_filename?: string
  active: boolean
}

interface WitsHierarchiesPageProps {
  embedded?: boolean
}

const WitsHierarchiesPage: React.FC<WitsHierarchiesPageProps> = ({ embedded = false }) => {
  const [hierarchies, setHierarchies] = useState<WitHierarchy[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Edit modal state
  const [editModal, setEditModal] = useState({
    isOpen: false,
    hierarchy: null as WitHierarchy | null
  })

  // Create modal state
  const [createModal, setCreateModal] = useState({
    isOpen: false
  })

  // Bulk edit modal state
  const [bulkEditModal, setBulkEditModal] = useState({
    isOpen: false
  })

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Filter states
  const [levelFilter, setLevelFilter] = useState('')
  const [nameFilter, setNameFilter] = useState('')
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

  // Filtered hierarchies based on filter states
  const filteredHierarchies = hierarchies.filter(hierarchy => {
    const matchesLevel = !levelFilter ||
      hierarchy.level.toString().includes(levelFilter)
    const matchesName = !nameFilter ||
      hierarchy.name.toLowerCase().includes(nameFilter.toLowerCase())
    const matchesIntegration = !integrationFilter ||
      (hierarchy.integration_name && hierarchy.integration_name.toLowerCase().includes(integrationFilter.toLowerCase()))
    // Status filter: if no filter selected, show all items (both active and inactive)
    const matchesStatus = !statusFilter ||
      (statusFilter === 'active' && hierarchy.active) ||
      (statusFilter === 'inactive' && !hierarchy.active)

    return matchesLevel && matchesName && matchesIntegration && matchesStatus
  })

  // Sort the filtered hierarchies
  const sortedHierarchies = [...filteredHierarchies].sort((a, b) => {
    if (!sortField) return 0

    let aVal: any = a[sortField as keyof WitHierarchy]
    let bVal: any = b[sortField as keyof WitHierarchy]

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

  // Load hierarchies from API
  const loadHierarchies = async () => {
    const response = await witsApi.getWitsHierarchies()
    setHierarchies(response.data)
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Load both hierarchies and integrations in parallel
        await Promise.all([
          loadHierarchies(),
          loadIntegrations()
        ])
        setError(null)
      } catch (err) {
        console.error('Error fetching data:', err)
        setError('Failed to load work item type hierarchies')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Toggle active status
  const handleToggleActive = async (hierarchyId: number, currentActive: boolean) => {
    const hierarchy = hierarchies.find(h => h.id === hierarchyId)
    if (!hierarchy) return

    const action = currentActive ? 'deactivate' : 'activate'
    const message = currentActive
      ? `Are you sure you want to deactivate "${hierarchy.name}"? Dependent WIT mappings will have their hierarchy reference cleared.`
      : `Are you sure you want to activate "${hierarchy.name}"?`

    confirmDelete(
      message,
      async () => {
        try {
          const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'
          const response = await fetch(`${API_BASE_URL}/app/etl/wits-hierarchies/${hierarchyId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('pulse_token')}`
            },
            body: JSON.stringify({ active: !currentActive })
          })

          if (!response.ok) {
            throw new Error(`Failed to ${action} hierarchy`)
          }

          // Update local state
          setHierarchies(prev => prev.map(h =>
            h.id === hierarchyId
              ? { ...h, active: !currentActive }
              : h
          ))

          showSuccess(
            `Hierarchy ${currentActive ? 'Deactivated' : 'Activated'}`,
            `The hierarchy has been ${currentActive ? 'deactivated' : 'activated'} successfully.`
          )
        } catch (err) {
          console.error(`Error ${action}ing hierarchy:`, err)
          showError(`${action.charAt(0).toUpperCase() + action.slice(1)} Failed`, `Failed to ${action} hierarchy. Please try again.`)
        }
      }
    )
  }

  // Handle edit
  const handleEdit = (hierarchyId: number) => {
    const hierarchy = hierarchies.find(h => h.id === hierarchyId)
    if (hierarchy) {
      setEditModal({
        isOpen: true,
        hierarchy
      })
    }
  }

  // Handle edit save
  const handleEditSave = async (formData: Record<string, any>) => {
    if (!editModal.hierarchy) return

    try {
      const updateData = {
        name: formData.name,
        level: parseInt(formData.level),
        description: formData.description || null,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null,
        active: formData.active
      }

      const response = await witsApi.updateWitHierarchy(editModal.hierarchy.id, updateData)

      // Get integration info from the frontend state (already loaded)
      const selectedIntegration = integrations.find(i => i.id === updateData.integration_id)

      // Update local state with response data plus integration info from frontend
      const updatedHierarchy = {
        ...(response.data || response),
        integration_name: selectedIntegration?.name || null,
        integration_logo: selectedIntegration?.logo_filename || null
      }

      setHierarchies(prev => prev.map(h =>
        h.id === editModal.hierarchy!.id
          ? updatedHierarchy
          : h
      ))

      showSuccess('Hierarchy Updated', 'The hierarchy has been updated successfully.')
      setEditModal({ isOpen: false, hierarchy: null })
    } catch (error) {
      console.error('Error updating hierarchy:', error)
      showError('Update Failed', 'Failed to update hierarchy. Please try again.')
    }
  }

  // Handle create save
  const handleCreateSave = async (formData: Record<string, any>) => {
    try {
      const createData = {
        name: formData.name,
        level: parseInt(formData.level),
        description: formData.description || null,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null
      }

      const response = await witsApi.createWitHierarchy(createData)

      // Get integration info from the frontend state (already loaded)
      const selectedIntegration = integrations.find(i => i.id === createData.integration_id)

      // Add new hierarchy to local state with integration info from frontend
      const newHierarchy = {
        ...(response.data || response),
        integration_name: selectedIntegration?.name || null,
        integration_logo: selectedIntegration?.logo_filename || null
      }

      setHierarchies(prev => [...prev, newHierarchy])

      showSuccess('Hierarchy Created', 'The hierarchy has been created successfully.')
      setCreateModal({ isOpen: false })
    } catch (error) {
      console.error('Error creating hierarchy:', error)
      showError('Create Failed', 'Failed to create hierarchy. Please try again.')
    }
  }

  // Handle delete
  const handleDelete = async (hierarchyId: number) => {
    const hierarchy = hierarchies.find(h => h.id === hierarchyId)
    if (!hierarchy) return

    confirmDelete(
      `Are you sure you want to delete "${hierarchy.name}"? Dependent WIT mappings will have their hierarchy reference cleared.`,
      async () => {
        try {
          const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'
          const response = await fetch(`${API_BASE_URL}/app/etl/wits-hierarchies/${hierarchyId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('pulse_token')}`,
              'Content-Type': 'application/json'
            }
          })

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to delete hierarchy' }))
            throw new Error(errorData.detail || 'Failed to delete hierarchy')
          }

          // Update local state only after successful API call
          setHierarchies(prev => prev.filter(h => h.id !== hierarchyId))
          showSuccess('Hierarchy Deleted', 'The hierarchy has been deleted successfully.')
        } catch (err) {
          console.error('Error deleting hierarchy:', err)
          showError('Deletion Failed', err instanceof Error ? err.message : 'Failed to delete hierarchy. Please try again.')
        }
      }
    )
  }

  // Handle bulk edit save
  const handleBulkEditSave = async (formData: Record<string, any>) => {
    try {
      const updateData: any = {}

      // Handle Level field
      if (formData.level) {
        updateData.level = parseInt(formData.level)
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

      // Don't proceed if no fields to update
      if (Object.keys(updateData).length === 0) {
        showError('No Changes', 'Please select at least one field to update.')
        return
      }

      // Use bulk update endpoint for better performance (single transaction)
      const hierarchyIds = Array.from(selectedIds)
      const response = await witsApi.bulkUpdateWitHierarchies(hierarchyIds, updateData)
      const updatedHierarchies = response.data || response

      // Update local state with API response data
      setHierarchies(prev => prev.map(h => {
        // Find the updated hierarchy in the response
        const updated = updatedHierarchies.find((uh: any) => uh.id === h.id)
        if (updated) {
          return {
            ...h,
            ...updated
          }
        }
        return h
      }))

      showSuccess('Bulk Update Complete', `Successfully updated ${selectedIds.size} ${selectedIds.size === 1 ? 'hierarchy' : 'hierarchies'}.`)
      setBulkEditModal({ isOpen: false })
      setSelectedIds(new Set())
    } catch (error: any) {
      console.error('Error bulk updating hierarchies:', error)
      showError('Bulk Update Failed', error.response?.data?.detail || 'Failed to update hierarchies. Please try again.')
    }
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return

    confirmDelete(
      `Are you sure you want to delete ${selectedIds.size} ${selectedIds.size === 1 ? 'hierarchy' : 'hierarchies'}?`,
      async () => {
        try {
          const hierarchyIds = Array.from(selectedIds)
          await witsApi.bulkDeleteWitHierarchies(hierarchyIds)
          await loadHierarchies()
          setSelectedIds(new Set())
          showSuccess('Bulk Delete Complete', `Successfully deleted ${hierarchyIds.length} ${hierarchyIds.length === 1 ? 'hierarchy' : 'hierarchies'}.`)
        } catch (err: any) {
          showError('Bulk Delete Failed', err.response?.data?.detail || 'Failed to delete hierarchies. Please try again.')
        }
      }
    )
  }



  const content = (
    <>
            {/* Content */}
            <div>
              {loading ? (
                <div className="text-center py-12">
                  <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-primary" />
                  <h2 className="text-2xl font-semibold text-primary mb-2">
                    Loading...
                  </h2>
                  <p className="text-secondary">
                    Fetching work item type hierarchies
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
                      {/* Level Number Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Level Number</label>
                        <input
                          type="number"
                          placeholder="Filter by level number..."
                          value={levelFilter}
                          onChange={(e) => setLevelFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Level Name Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Level Name</label>
                        <input
                          type="text"
                          placeholder="Filter by level name..."
                          value={nameFilter}
                          onChange={(e) => setNameFilter(e.target.value)}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
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

                  {/* WIT Hierarchies Table */}
                  <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
                    {/* Sticky Header Section (Title + Column Headers) */}
                    <div className="sticky top-16 z-20 bg-table-container">
                      <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
                        <h2 className="text-lg font-semibold text-table-header">Work Item Type Hierarchies</h2>
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
                            onClick={() => {
                              if (integrations.length === 0) {
                                showError('No Integrations Available', 'Please configure at least one data integration before creating hierarchies.')
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
                            <span className="text-sm font-medium text-primary">Create Hierarchy</span>
                          </button>
                        </div>
                      </div>

                      {/* Column Headers */}
                      <div className="overflow-x-auto bg-table-column-header">
                        <table className="w-full" style={{ tableLayout: 'fixed' }}>
                          <colgroup>
                            <col style={{ width: '5%' }} />
                            <col style={{ width: '9%' }} />
                            <col style={{ width: '18%' }} />
                            <col style={{ width: '28%' }} />
                            <col style={{ width: '15%' }} />
                            <col style={{ width: '12%' }} />
                            <col style={{ width: '13%' }} />
                          </colgroup>
                          <thead className="bg-table-column-header">
                            <tr className="bg-table-column-header">
                            <th className="px-4 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                              <input
                                type="checkbox"
                                checked={selectedIds.size > 0 && selectedIds.size === sortedHierarchies.length}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedIds(new Set(sortedHierarchies.map(h => h.id)))
                                  } else {
                                    setSelectedIds(new Set())
                                  }
                                }}
                                className="w-4 h-4 bg-secondary border-gray-400 rounded cursor-pointer"
                                style={{ accentColor: 'var(--color-1)' }}
                              />
                            </th>
                            <th
                              className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('level')}
                            >
                              <div className="flex items-center justify-center gap-2">
                                Level
                                {sortField === 'level' ? (
                                  sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </div>
                            </th>
                            <th
                              className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('name')}
                            >
                              <div className="flex items-center gap-2">
                                Name
                                {sortField === 'name' ? (
                                  sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </div>
                            </th>
                            <th
                              className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                              onClick={() => handleSort('description')}
                            >
                              <div className="flex items-center gap-2">
                                Description
                                {sortField === 'description' ? (
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
                          <col style={{ width: '9%' }} />
                          <col style={{ width: '18%' }} />
                          <col style={{ width: '28%' }} />
                          <col style={{ width: '15%' }} />
                          <col style={{ width: '12%' }} />
                          <col style={{ width: '13%' }} />
                        </colgroup>
                        <tbody>
                          {sortedHierarchies.length === 0 ? (
                            <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                              <td colSpan={7} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                                <div className="text-6xl mb-4">⚡</div>
                                <p className="text-lg mb-2">No hierarchies found</p>
                                <p className="text-sm">Try adjusting your filters or create a new hierarchy</p>
                              </td>
                            </tr>
                          ) : (
                            sortedHierarchies.map((hierarchy, index) => (
                              <tr
                                key={hierarchy.id}
                                className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!hierarchy.active ? 'opacity-50' : ''}`}
                              >
                              <td className="px-4 py-5 whitespace-nowrap text-center">
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(hierarchy.id)}
                                  onChange={(e) => {
                                    const newSelected = new Set(selectedIds)
                                    if (e.target.checked) {
                                      newSelected.add(hierarchy.id)
                                    } else {
                                      newSelected.delete(hierarchy.id)
                                    }
                                    setSelectedIds(newSelected)
                                  }}
                                  className="w-4 h-4 bg-secondary border-gray-400 rounded cursor-pointer"
                                  style={{ accentColor: 'var(--color-1)' }}
                                />
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row font-semibold">{hierarchy.level}</td>
                              <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{hierarchy.name}</td>
                              <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row">{hierarchy.description || '-'}</td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="flex items-center justify-center">
                                  <IntegrationLogo
                                    logoFilename={hierarchy.integration_logo}
                                    integrationName={hierarchy.integration_name}
                                  />
                                  {!hierarchy.integration_logo && (
                                    <span className="text-sm text-table-row">
                                      {hierarchy.integration_name || '-'}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="job-toggle-switch" onClick={() => handleToggleActive(hierarchy.id, hierarchy.active)}>
                                  <div className={`toggle-switch ${hierarchy.active ? 'active' : ''}`}>
                                    <div className="toggle-slider"></div>
                                  </div>
                                  <span className="toggle-label">{hierarchy.active ? 'On' : 'Off'}</span>
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="flex items-center justify-center space-x-3">
                                  <button
                                    onClick={() => handleEdit(hierarchy.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                                    aria-label="Edit hierarchy"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                    </svg>
                                  </button>
                                  <button
                                    onClick={() => handleDelete(hierarchy.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-red-500 shadow-sm hover:shadow-md transition-all"
                                    aria-label="Delete hierarchy"
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
                  </div>
                </>
              )}
            </div>



      {/* Edit Modal */}
      {editModal.hierarchy && (
        <EditModal
          isOpen={editModal.isOpen}
          onClose={() => setEditModal({ isOpen: false, hierarchy: null })}
          onSave={handleEditSave}
          title="Edit Hierarchy"
          fields={[
            {
              name: 'name',
              label: 'Level Name',
              type: 'text',
              value: editModal.hierarchy.name,
              required: true,
              placeholder: 'Enter level name'
            },
            {
              name: 'level',
              label: 'Level Number',
              type: 'number',
              value: editModal.hierarchy.level,
              required: true,
              placeholder: 'Enter level number'
            },
            {
              name: 'description',
              label: 'Description',
              type: 'textarea',
              value: editModal.hierarchy.description || '',
              placeholder: 'Enter description (optional)'
            },
            {
              name: 'integration_id',
              label: 'Integration',
              type: 'select',
              value: editModal.hierarchy.integration_id ? editModal.hierarchy.integration_id.toString() : '',
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
              value: editModal.hierarchy.active,
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
        title="Create Hierarchy"
        fields={[
          {
            name: 'name',
            label: 'Level Name',
            type: 'text',
            required: true,
            placeholder: 'Enter level name'
          },
          {
            name: 'level',
            label: 'Level Number',
            type: 'number',
            required: true,
            placeholder: 'Enter level number'
          },
          {
            name: 'description',
            label: 'Description',
            type: 'textarea',
            placeholder: 'Enter description (optional)'
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
          }
        ]}
      />

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={bulkEditModal.isOpen}
        onClose={() => setBulkEditModal({ isOpen: false })}
        onSave={handleBulkEditSave}
        title={`Bulk Edit ${selectedIds.size} ${selectedIds.size === 1 ? 'Hierarchy' : 'Hierarchies'}`}
        fields={[
          {
            name: 'level',
            label: 'Level',
            type: 'number',
            required: false,
            placeholder: 'Leave empty to keep current values'
          },
          {
            name: 'integration_id',
            label: 'Integration',
            type: 'select',
            required: false,
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
            required: false,
            placeholder: 'Select active status',
            options: [
              { value: 'true', label: '✓ Activate' },
              { value: 'false', label: '✗ Deactivate' }
            ]
          }
        ]}
      />

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmation.isOpen}
        onClose={hideConfirmation}
        onConfirm={confirmation.onConfirm}
        title="Confirm Action"
        message={confirmation.message}
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

export default WitsHierarchiesPage
