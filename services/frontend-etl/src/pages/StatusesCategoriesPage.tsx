import React, { useState, useEffect } from 'react'
import { statusesApi, integrationsApi } from '../services/etlApiService'
import CreateModal from '../components/CreateModal'
import EditModal from '../components/EditModal'
import ConfirmationModal from '../components/ConfirmationModal'
import BulkEditModal from '../components/BulkEditModal'
import BackToTop from '../components/BackToTop'
import ToastContainer from '../components/ToastContainer'
import IntegrationLogo from '../components/IntegrationLogo'
import { useToast } from '../hooks/useToast'
import { useConfirmation } from '../hooks/useConfirmation'
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react'

interface StatusCategory {
  id: number
  name: string
  description: string | null
  is_waiting: boolean
  is_done: boolean
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

interface StatusesCategoriesPageProps {
  embedded?: boolean
}

const StatusesCategoriesPage: React.FC<StatusesCategoriesPageProps> = ({ embedded = false }) => {
  const [categories, setCategories] = useState<StatusCategory[]>([])
  const [filteredCategories, setFilteredCategories] = useState<StatusCategory[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Filter states
  const [searchTerm, setSearchTerm] = useState('')
  const [showActiveOnly, setShowActiveOnly] = useState(false)

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<StatusCategory | null>(null)

  // Bulk edit modal state
  const [bulkEditModal, setBulkEditModal] = useState({
    isOpen: false
  })

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Sort states
  const [sortField, setSortField] = useState<string | null>('name')
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

  // Load categories
  const loadCategories = async () => {
    try {
      setIsLoading(true)
      const response = await statusesApi.getStatusCategories()
      setCategories(response.data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load status categories')
      console.error('Error loading status categories:', err)
    } finally {
      setIsLoading(false)
    }
  }

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
      await Promise.all([loadCategories(), loadIntegrations()])
    }
    fetchData()
  }, [])

  // Apply filters
  useEffect(() => {
    let result = [...categories]

    // Search filter
    if (searchTerm) {
      result = result.filter(cat =>
        cat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (cat.description && cat.description.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    // Active filter
    if (showActiveOnly) {
      result = result.filter(cat => cat.active)
    }

    setFilteredCategories(result)
  }, [categories, searchTerm, showActiveOnly])

  // Sort the filtered categories
  const sortedCategories = [...filteredCategories].sort((a, b) => {
    if (!sortField) return 0

    let aVal: any = a[sortField as keyof StatusCategory]
    let bVal: any = b[sortField as keyof StatusCategory]

    // Handle null/undefined
    if (aVal === null || aVal === undefined) aVal = ''
    if (bVal === null || bVal === undefined) bVal = ''

    // Convert to string for comparison
    if (typeof aVal === 'string') aVal = aVal.toLowerCase()
    if (typeof bVal === 'string') bVal = bVal.toLowerCase()

    // Compare
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  const handleToggleActive = async (id: number, currentActive: boolean) => {
    try {
      await statusesApi.toggleStatusCategory(id)
      await loadCategories()
      showSuccess(`Status category ${currentActive ? 'deactivated' : 'activated'} successfully`)
    } catch (err: any) {
      showError(err.response?.data?.detail || 'Failed to toggle category status')
    }
  }

  const handleEdit = (id: number) => {
    const category = categories.find(c => c.id === id)
    if (category) {
      setSelectedCategory(category)
      setIsEditModalOpen(true)
    }
  }

  const handleDelete = async (categoryId: number) => {
    const category = categories.find(c => c.id === categoryId)
    if (!category) return

    confirmDelete(
      `Are you sure you want to delete the status category "${category.name}"?`,
      async () => {
        try {
          await statusesApi.deleteStatusCategory(categoryId)
          await loadCategories()
          showSuccess('Status category deleted successfully')
        } catch (err: any) {
          showError(err.response?.data?.detail || 'Failed to delete status category')
        }
      }
    )
  }

  // Handle bulk edit save
  const handleBulkEditSave = async (formData: Record<string, any>) => {
    try {
      const updateData: any = {}

      // Handle Is Waiting field
      if (formData.is_waiting) {
        updateData.is_waiting = formData.is_waiting === 'true'
      }

      // Handle Is Done field
      if (formData.is_done) {
        updateData.is_done = formData.is_done === 'true'
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
      const categoryIds = Array.from(selectedIds)
      const response = await statusesApi.bulkUpdateStatusCategories(categoryIds, updateData)
      const updatedCategories = response.data || response

      // Update local state with API response data
      setCategories(prev => prev.map(c => {
        // Find the updated category in the response
        const updated = updatedCategories.find((uc: any) => uc.id === c.id)
        if (updated) {
          return {
            ...c,
            ...updated
          }
        }
        return c
      }))

      showSuccess('Bulk Update Complete', `Successfully updated ${selectedIds.size} status ${selectedIds.size === 1 ? 'category' : 'categories'}.`)
      setBulkEditModal({ isOpen: false })
      setSelectedIds(new Set())
    } catch (error) {
      console.error('Error bulk updating categories:', error)
      showError('Bulk Update Failed', 'Failed to update status categories. Please try again.')
    }
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return

    confirmDelete(
      `Are you sure you want to delete ${selectedIds.size} status ${selectedIds.size === 1 ? 'category' : 'categories'}?`,
      async () => {
        try {
          const categoryIds = Array.from(selectedIds)
          await statusesApi.bulkDeleteStatusCategories(categoryIds)
          await loadCategories()
          setSelectedIds(new Set())
          showSuccess('Bulk Delete Complete', `Successfully deleted ${categoryIds.length} status ${categoryIds.length === 1 ? 'category' : 'categories'}.`)
        } catch (err: any) {
          showError('Bulk Delete Failed', err.response?.data?.detail || 'Failed to delete status categories. Please try again.')
        }
      }
    )
  }

  const handleCreateSubmit = async (data: any) => {
    try {
      const createData = {
        ...data,
        integration_id: data.integration_id ? parseInt(data.integration_id) : null
      }
      await statusesApi.createStatusCategory(createData)
      await loadCategories()
      setIsCreateModalOpen(false)
      showSuccess('Status category created successfully')
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Failed to create status category')
    }
  }

  const handleEditSubmit = async (data: any) => {
    if (!selectedCategory) return
    try {
      const updateData = {
        ...data,
        integration_id: data.integration_id ? parseInt(data.integration_id) : null
      }
      await statusesApi.updateStatusCategory(selectedCategory.id, updateData)
      await loadCategories()
      setIsEditModalOpen(false)
      setSelectedCategory(null)
      showSuccess('Status category updated successfully')
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Failed to update status category')
    }
  }

  // Custom render for all toggle switches (create modal - 2 toggles)
  const renderTogglesCreate = (
    field: any,
    formData: Record<string, any>,
    handleInputChange: (name: string, value: any) => void,
    errors: Record<string, string>
  ) => {
    return (
      <div className="space-y-3">
        {/* Is Waiting Toggle */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-secondary whitespace-nowrap w-24">
            Is Waiting
          </label>
          <div
            className="job-toggle-switch cursor-pointer"
            onClick={() => handleInputChange('is_waiting', !formData.is_waiting)}
          >
            <div className={`toggle-switch ${formData.is_waiting ? 'active' : ''}`}>
              <div className="toggle-slider"></div>
            </div>
            <span className="toggle-label">{formData.is_waiting ? 'Yes' : 'No'}</span>
          </div>
        </div>

        {/* Is Done Toggle */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-secondary whitespace-nowrap w-24">
            Is Done
          </label>
          <div
            className="job-toggle-switch cursor-pointer"
            onClick={() => handleInputChange('is_done', !formData.is_done)}
          >
            <div className={`toggle-switch ${formData.is_done ? 'active' : ''}`}>
              <div className="toggle-slider"></div>
            </div>
            <span className="toggle-label">{formData.is_done ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </div>
    )
  }

  // Custom render for all toggle switches (edit modal - 3 toggles)
  const renderTogglesEdit = (
    field: any,
    formData: Record<string, any>,
    handleInputChange: (name: string, value: any) => void,
    errors: Record<string, string>
  ) => {
    return (
      <div className="space-y-3">
        {/* Is Waiting Toggle */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-secondary whitespace-nowrap w-24">
            Is Waiting
          </label>
          <div
            className="job-toggle-switch cursor-pointer"
            onClick={() => handleInputChange('is_waiting', !formData.is_waiting)}
          >
            <div className={`toggle-switch ${formData.is_waiting ? 'active' : ''}`}>
              <div className="toggle-slider"></div>
            </div>
            <span className="toggle-label">{formData.is_waiting ? 'Yes' : 'No'}</span>
          </div>
        </div>

        {/* Is Done Toggle */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-secondary whitespace-nowrap w-24">
            Is Done
          </label>
          <div
            className="job-toggle-switch cursor-pointer"
            onClick={() => handleInputChange('is_done', !formData.is_done)}
          >
            <div className={`toggle-switch ${formData.is_done ? 'active' : ''}`}>
              <div className="toggle-slider"></div>
            </div>
            <span className="toggle-label">{formData.is_done ? 'Yes' : 'No'}</span>
          </div>
        </div>

        {/* Active Toggle */}
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
      </div>
    )
  }

  const createFields = [
    { name: 'name', label: 'Name', type: 'text' as const, required: true },
    { name: 'description', label: 'Description', type: 'textarea' as const, required: false },
    {
      name: 'integration_id',
      label: 'Integration',
      type: 'select' as const,
      required: false,
      options: [
        { value: '', label: '- No Integration -' },
        ...integrations.map(integration => ({
          value: integration.id.toString(),
          label: integration.name
        }))
      ]
    },
    // Hidden fields to store the actual values (default to false)
    { name: 'is_waiting', label: '', type: 'text' as const, required: false, defaultValue: false, customRender: () => null },
    { name: 'is_done', label: '', type: 'text' as const, required: false, defaultValue: false, customRender: () => null },
    {
      name: 'toggles',
      label: '',
      type: 'text' as const,
      required: false,
      customRender: renderTogglesCreate
    },
  ]

  // Generate edit fields with current values
  const getEditFields = () => {
    if (!selectedCategory) return []

    // We need to pass the initial values for the toggles through hidden fields
    // and then use customRender to display them
    return [
      { name: 'name', label: 'Name', type: 'text' as const, value: selectedCategory.name, required: true },
      { name: 'description', label: 'Description', type: 'textarea' as const, value: selectedCategory.description || '', required: false },
      {
        name: 'integration_id',
        label: 'Integration',
        type: 'select' as const,
        value: selectedCategory.integration_id ? selectedCategory.integration_id.toString() : '',
        required: false,
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
      // Hidden fields to store the actual values
      { name: 'is_waiting', label: '', type: 'text' as const, value: selectedCategory.is_waiting, required: false, customRender: () => null },
      { name: 'is_done', label: '', type: 'text' as const, value: selectedCategory.is_done, required: false, customRender: () => null },
      { name: 'active', label: '', type: 'text' as const, value: selectedCategory.active, required: false, customRender: () => null },
      {
        name: 'toggles',
        label: '',
        type: 'text' as const,
        value: '',
        required: false,
        customRender: renderTogglesEdit
      },
    ]
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-secondary">Loading status categories...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-primary rounded-lg shadow-md p-6 border border-gray-400">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-secondary mb-2">Search</label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name or description..."
              className="w-full px-4 py-2 rounded bg-secondary text-primary border border-gray-400 focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          <div className="flex items-end">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showActiveOnly}
                onChange={(e) => setShowActiveOnly(e.target.checked)}
                className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent"
              />
              <span className="text-sm font-medium text-secondary">Show Active Only</span>
            </label>
          </div>

          <div className="flex items-end justify-end">
            <div className="text-sm text-secondary">
              Showing {sortedCategories.length} of {categories.length} categories
            </div>
          </div>
        </div>
      </div>

      {/* Status Categories Table */}
      <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
        {/* Sticky Header Section */}
        <div className="sticky top-16 z-20 bg-table-container">
          <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
            <h2 className="text-lg font-semibold text-table-header">Status Categories</h2>
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
                onClick={() => setIsCreateModalOpen(true)}
                className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                  <path d="M5 12h14"></path>
                  <path d="M12 5v14"></path>
                </svg>
                <span className="text-sm font-medium text-primary">Create Category</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto bg-table-column-header">
            <table className="w-full" style={{ tableLayout: 'fixed' }}>
              <colgroup>
                <col style={{ width: '5%' }} />
                <col style={{ width: '18%' }} />
                <col style={{ width: '27%' }} />
                <col style={{ width: '10%' }} />
                <col style={{ width: '10%' }} />
                <col style={{ width: '12%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '10%' }} />
              </colgroup>
              <thead className="bg-table-column-header">
              <tr className="bg-table-column-header">
                <th className="px-4 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                  <input
                    type="checkbox"
                    checked={selectedIds.size > 0 && selectedIds.size === sortedCategories.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedIds(new Set(sortedCategories.map(c => c.id)))
                      } else {
                        setSelectedIds(new Set())
                      }
                    }}
                    className="w-4 h-4 bg-secondary border-gray-400 rounded cursor-pointer"
                    style={{ accentColor: 'var(--color-1)' }}
                  />
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
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">Description</th>
                <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Is Waiting</th>
                <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Is Done</th>
                <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Integration</th>
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
              <col style={{ width: '18%' }} />
              <col style={{ width: '27%' }} />
              <col style={{ width: '10%' }} />
              <col style={{ width: '10%' }} />
              <col style={{ width: '12%' }} />
              <col style={{ width: '8%' }} />
              <col style={{ width: '10%' }} />
            </colgroup>
            <tbody>
              {sortedCategories.length === 0 ? (
                <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                  <td colSpan={8} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                    <div className="text-6xl mb-4">⚡</div>
                    <p className="text-lg mb-2">No status categories found</p>
                    <p className="text-sm">Try adjusting your filters or create a new status category</p>
                  </td>
                </tr>
              ) : (
                sortedCategories.map((category, index) => (
                  <tr
                    key={category.id}
                    className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!category.active ? 'opacity-50' : ''}`}
                  >
                    <td className="px-4 py-5 whitespace-nowrap text-center">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(category.id)}
                        onChange={(e) => {
                          const newSelectedIds = new Set(selectedIds)
                          if (e.target.checked) {
                            newSelectedIds.add(category.id)
                          } else {
                            newSelectedIds.delete(category.id)
                          }
                          setSelectedIds(newSelectedIds)
                        }}
                        className="w-4 h-4 bg-secondary border-gray-400 rounded cursor-pointer"
                        style={{ accentColor: 'var(--color-1)' }}
                      />
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{category.name}</td>
                    <td className="px-6 py-5 text-sm text-table-row">{category.description || '-'}</td>
                    <td className="px-6 py-5 whitespace-nowrap text-center">
                      <span className={`px-2 py-1 text-xs rounded ${category.is_waiting ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}`}>
                        {category.is_waiting ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-center">
                      <span className={`px-2 py-1 text-xs rounded ${category.is_done ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}`}>
                        {category.is_done ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-center">
                      {category.integration_id && category.integration_logo ? (
                        <div className="flex items-center justify-center">
                          <IntegrationLogo
                            logoFilename={category.integration_logo}
                            integrationName={category.integration_name || ''}
                            size="sm"
                          />
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-center">
                      <div
                        className="job-toggle-switch cursor-pointer"
                        onClick={() => handleToggleActive(category.id, category.active)}
                      >
                        <div className={`toggle-switch ${category.active ? 'active' : ''}`}>
                          <div className="toggle-slider"></div>
                        </div>
                        <span className="toggle-label">{category.active ? 'On' : 'Off'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-center">
                      <div className="flex items-center justify-center space-x-2">
                        <button
                          onClick={() => handleEdit(category.id)}
                          className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                          title="Edit"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(category.id)}
                          className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-red-500 shadow-sm hover:shadow-md transition-all"
                          title="Delete"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M10 11v6"></path>
                            <path d="M14 11v6"></path>
                            <path d="M3 6h18"></path>
                            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
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

      {/* Modals */}
      <CreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSave={handleCreateSubmit}
        title="Create Status Category"
        fields={createFields}
      />

      {selectedCategory && (
        <EditModal
          isOpen={isEditModalOpen}
          onClose={() => {
            setIsEditModalOpen(false)
            setSelectedCategory(null)
          }}
          onSave={handleEditSubmit}
          title="Edit Status Category"
          fields={getEditFields()}
        />
      )}

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={bulkEditModal.isOpen}
        onClose={() => setBulkEditModal({ isOpen: false })}
        onSave={handleBulkEditSave}
        title="Bulk Edit Status Categories"
        selectedCount={selectedIds.size}
        fields={[
          {
            name: 'is_waiting',
            label: 'Is Waiting',
            type: 'select',
            placeholder: 'Select waiting status',
            options: [
              { value: 'true', label: '✓ Yes' },
              { value: 'false', label: '✗ No' }
            ]
          },
          {
            name: 'is_done',
            label: 'Is Done',
            type: 'select',
            placeholder: 'Select done status',
            options: [
              { value: 'true', label: '✓ Yes' },
              { value: 'false', label: '✗ No' }
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
      />

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Back to Top Button */}
      <BackToTop />
    </div>
  )
}

export default StatusesCategoriesPage

