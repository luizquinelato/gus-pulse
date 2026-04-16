import React, { useState, useEffect } from 'react'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import Header from '../components/Header'
import CollapsedSidebar from '../components/CollapsedSidebar'
import DependencyModal from '../components/DependencyModal'
import ConfirmationModal from '../components/ConfirmationModal'
import WorkflowModal from '../components/WorkflowModal'
import BulkEditModal from '../components/BulkEditModal'
import BackToTop from '../components/BackToTop'
import ToastContainer from '../components/ToastContainer'
import IntegrationLogo from '../components/IntegrationLogo'
import { useToast } from '../hooks/useToast'
import { useConfirmation } from '../hooks/useConfirmation'
import { statusesApi, integrationsApi } from '../services/etlApiService'

interface Workflow {
  id: number
  name: string
  integration_id?: number
  integration_name?: string
  integration_logo?: string
  active: boolean
}

interface WorkflowStep {
  id: number
  workflow_id: number
  workflow_name?: string
  name: string
  order?: number
  status_id?: number
  status_name?: string
  is_commitment_point: boolean
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

interface WorkflowsPageProps {
  embedded?: boolean
}

const WorkflowsPage: React.FC<WorkflowsPageProps> = ({ embedded = false }) => {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [statuses, setStatuses] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Filter states
  const [filters, setFilters] = useState({
    name: '',
    integration: '',
    status: ''
  })

  // Workflow Steps Modal state
  const [stepsModal, setStepsModal] = useState({
    isOpen: false,
    workflow: null as Workflow | null,
    steps: [] as WorkflowStep[]
  })

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

  // Workflow modal state (unified create/edit)
  const [workflowModal, setWorkflowModal] = useState({
    isOpen: false,
    workflow: null as Workflow | null,
    existingSteps: [] as WorkflowStep[]
  })

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Bulk edit modal state
  const [bulkEditModal, setBulkEditModal] = useState({
    isOpen: false
  })

  // Dependency modal state
  const [dependencyModal, setDependencyModal] = useState({
    isOpen: false,
    workflowId: null as number | null,
    workflowName: '',
    action: 'deactivate' as 'deactivate' | 'activate',
    dependencies: [] as any[],
    reassignmentTargets: [] as any[]
  })

  // Handler functions
  const checkDependencies = async (workflowId: number): Promise<any> => {
    try {
      // TODO: Implement actual dependency checking API call
      return {
        has_dependencies: Math.random() > 0.7,
        dependency_count: Math.floor(Math.random() * 3) + 1,
        affected_items_count: Math.floor(Math.random() * 10) + 1,
        reassignment_targets: workflows.filter(w => w.id !== workflowId && w.active).slice(0, 3)
      }
    } catch (error) {
      console.error('Error checking dependencies:', error)
      throw new Error('Failed to check dependencies')
    }
  }

  const handleToggleActive = async (workflowId: number, currentActive: boolean) => {
    try {
      const workflow = workflows.find(w => w.id === workflowId)
      if (!workflow) return

      if (currentActive) {
        // Deactivating - check for dependencies
        const dependencyData = await checkDependencies(workflowId)

        if (dependencyData.has_dependencies) {
          setDependencyModal({
            isOpen: true,
            workflowId,
            workflowName: workflow.name,
            action: 'deactivate',
            dependencies: dependencyData.dependent_mappings || [],
            reassignmentTargets: dependencyData.reassignment_targets || []
          })
          return
        }
      }

      // No dependencies or activating - proceed directly
      await performToggle(workflowId, !currentActive)
    } catch (error) {
      console.error('Error toggling workflow:', error)
      showError('Toggle Failed', 'Failed to toggle workflow status. Please try again.')
    }
  }

  const performToggle = async (workflowId: number, newActiveState: boolean) => {
    try {
      // TODO: Implement actual API call when backend endpoint is ready
      // For now, just update local state after a small delay to simulate API call
      await new Promise(resolve => setTimeout(resolve, 100))

      // Update local state only after "API call" succeeds
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? { ...workflow, active: newActiveState }
          : workflow
      ))

      setDependencyModal(prev => ({ ...prev, isOpen: false }))
      showSuccess(
        `Workflow ${newActiveState ? 'Activated' : 'Deactivated'}`,
        `The workflow has been ${newActiveState ? 'activated' : 'deactivated'} successfully.`
      )
    } catch (error) {
      console.error('Error updating workflow:', error)
      showError('Update Failed', 'Failed to update workflow status. Please try again.')
    }
  }

  // Handle view steps
  const handleViewSteps = async (workflow: Workflow) => {
    try {
      // Fetch workflow steps for this specific workflow
      const response = await statusesApi.getWorkflowSteps()
      const allSteps = response.data || []

      // Filter steps for this workflow
      const workflowSteps = allSteps.filter((step: WorkflowStep) => step.workflow_id === workflow.id)

      setStepsModal({
        isOpen: true,
        workflow,
        steps: workflowSteps
      })
    } catch (error) {
      console.error('Error fetching workflow steps:', error)
      showError('Load Failed', 'Failed to load workflow steps. Please try again.')
    }
  }

  // Handle edit - open modal with workflow and its steps
  const handleEdit = async (workflowId: number) => {
    const workflow = workflows.find(w => w.id === workflowId)
    if (!workflow) return

    try {
      // Fetch existing steps for this workflow
      const response = await statusesApi.getWorkflowSteps()
      const allSteps = response.data || []
      const workflowSteps = allSteps.filter((step: WorkflowStep) => step.workflow_id === workflowId)

      setWorkflowModal({
        isOpen: true,
        workflow,
        existingSteps: workflowSteps
      })
    } catch (error) {
      console.error('Error loading workflow steps:', error)
      showError('Load Failed', 'Failed to load workflow steps. Please try again.')
    }
  }

  // Handle create - open modal for new workflow
  const handleCreate = () => {
    setWorkflowModal({
      isOpen: true,
      workflow: null,
      existingSteps: []
    })
  }

  // Handle workflow save (create or update)
  const handleWorkflowSave = async (workflowData: any, steps: any[]) => {
    try {
      let workflowId: number
      let isNewWorkflow = false

      // Step 1: Save workflow (create or update)
      if (workflowModal.workflow) {
        // Update existing workflow
        const response = await statusesApi.updateWorkflow(workflowModal.workflow.id, workflowData)
        workflowId = workflowModal.workflow.id

        // Get integration info
        const selectedIntegration = integrations.find(i => i.id === workflowData.integration_id)

        // Update local state
        const updatedWorkflow = {
          ...(response.data || response),
          integration_name: selectedIntegration?.name || null,
          integration_logo: selectedIntegration?.logo_filename || null
        }

        setWorkflows(prev => prev.map(w =>
          w.id === workflowId ? updatedWorkflow : w
        ))
      } else {
        // Create new workflow
        const response = await statusesApi.createWorkflow(workflowData)
        const newWorkflowData = response.data || response
        workflowId = newWorkflowData.id
        isNewWorkflow = true

        // Get integration info
        const selectedIntegration = integrations.find(i => i.id === workflowData.integration_id)

        // Add to local state
        const newWorkflow = {
          ...newWorkflowData,
          integration_name: selectedIntegration?.name || null,
          integration_logo: selectedIntegration?.logo_filename || null
        }

        setWorkflows(prev => [...prev, newWorkflow])
      }

      // Step 2: Save workflow steps
      if (steps.length > 0) {
        // IMPORTANT: Handle commitment point changes carefully to avoid unique constraint violation
        // (only one step can have is_commitment_point=true per workflow)

        // Find which step currently has commitment point (from existing steps)
        const oldCommitmentStep = workflowModal.existingSteps.find(s => s.is_commitment_point)
        const newCommitmentStep = steps.find(s => s.is_commitment_point && !s._isDeleted)
        const commitmentPointChanged = oldCommitmentStep?.id !== newCommitmentStep?.id

        // If commitment point changed, turn off the old one first
        if (commitmentPointChanged && oldCommitmentStep?.id && oldCommitmentStep.id !== newCommitmentStep?.id) {
          await statusesApi.updateWorkflowStep(oldCommitmentStep.id, {
            workflow_id: workflowId,
            name: oldCommitmentStep.name,
            order: oldCommitmentStep.order,
            status_id: oldCommitmentStep.status_id || null,
            is_commitment_point: false,
            integration_id: workflowData.integration_id,
            active: oldCommitmentStep.active !== undefined ? oldCommitmentStep.active : true
          })
        }

        // Now update/create all steps with their final values
        for (const step of steps) {
          if (step._isDeleted) continue

          const stepData = {
            workflow_id: workflowId,
            name: step.name,
            order: step.order,
            status_id: step.status_id || null,
            is_commitment_point: step.is_commitment_point,
            integration_id: workflowData.integration_id,
            active: step.active !== undefined ? step.active : true
          }

          if (step.id && !step._isNew) {
            // Update existing step
            await statusesApi.updateWorkflowStep(step.id, stepData)
          } else if (step._isNew) {
            // Create new step
            await statusesApi.createWorkflowStep(stepData)
          }
        }

        // Delete steps marked for deletion
        const deletedSteps = workflowModal.existingSteps.filter(
          existingStep => !steps.find(s => s.id === existingStep.id && !s._isDeleted)
        )
        for (const step of deletedSteps) {
          if (step.id) {
            await statusesApi.deleteWorkflowStep(step.id)
          }
        }
      }

      showSuccess(
        isNewWorkflow ? 'Workflow Created' : 'Workflow Updated',
        `The workflow has been ${isNewWorkflow ? 'created' : 'updated'} successfully.`
      )

      setWorkflowModal({ isOpen: false, workflow: null, existingSteps: [] })
    } catch (error) {
      console.error('Error saving workflow:', error)
      showError('Save Failed', 'Failed to save workflow. Please try again.')
      throw error
    }
  }

  // Handle delete
  const handleDelete = async (workflowId: number) => {
    const workflow = workflows.find(w => w.id === workflowId)
    if (!workflow) return

    confirmDelete(
      workflow.name,
      async () => {
        try {
          const response = await statusesApi.deleteWorkflow(workflowId)

          // Remove from local state
          setWorkflows(prev => prev.filter(w => w.id !== workflowId))

          // Show success message from backend
          const message = response.data?.message || 'Workflow deleted successfully.'
          showSuccess('Workflow Deleted', message)
        } catch (error) {
          console.error('Error deleting workflow:', error)
          showError('Delete Failed', 'Failed to delete workflow. Please try again.')
        }
      }
    )
  }

  // Handle bulk edit save
  const handleBulkEditSave = async (formData: Record<string, any>) => {
    try {
      const updateData: any = {}

      // Handle Integration field - only update if a value is selected
      if (formData.integration_id && formData.integration_id !== '') {
        if (formData.integration_id === '__CLEAR__') {
          updateData.integration_id = null
        } else {
          updateData.integration_id = parseInt(formData.integration_id)
        }
      }

      // Handle Active field - only update if a value is selected
      if (formData.active && formData.active !== '') {
        updateData.active = formData.active === 'true'
      }

      const workflowIds = Array.from(selectedIds)
      await statusesApi.bulkUpdateWorkflows(workflowIds, updateData)

      // Refresh workflows list
      const response = await statusesApi.getWorkflows()
      setWorkflows(response.data)

      setBulkEditModal({ isOpen: false })
      setSelectedIds(new Set())
      showSuccess('Bulk Edit Successful', `Successfully updated ${workflowIds.length} workflow(s).`)
    } catch (err: any) {
      console.error('Error bulk editing workflows:', err)
      showError('Bulk Edit Failed', err.response?.data?.detail || 'Failed to update workflows. Please try again.')
    }
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    confirmDelete(
      `Are you sure you want to delete ${selectedIds.size} workflow(s)? Workflows with dependent WITs will be deactivated instead.`,
      async () => {
        try {
          const workflowIds = Array.from(selectedIds)
          const response = await statusesApi.bulkDeleteWorkflows(workflowIds)

          // Refresh workflows list
          const refreshResponse = await statusesApi.getWorkflows()
          setWorkflows(refreshResponse.data)

          setSelectedIds(new Set())

          const result = response.data
          const message = result.deleted > 0 && result.deactivated > 0
            ? `Deleted ${result.deleted} workflow(s), deactivated ${result.deactivated} workflow(s) with dependencies`
            : result.deleted > 0
            ? `Deleted ${result.deleted} workflow(s)`
            : `Deactivated ${result.deactivated} workflow(s) with dependencies`

          showSuccess('Bulk Delete Successful', message)
        } catch (err: any) {
          console.error('Error bulk deleting workflows:', err)
          showError('Bulk Delete Failed', err.response?.data?.detail || 'Failed to delete workflows. Please try again.')
        }
      }
    )
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
      try {
        setLoading(true)
        // Load workflows, integrations, and statuses in parallel
        await Promise.all([
          (async () => {
            const response = await statusesApi.getWorkflows()
            setWorkflows(response.data)
          })(),
          (async () => {
            const response = await statusesApi.getStatuses()
            setStatuses(response.data || [])
          })(),
          loadIntegrations()
        ])
        setError(null)
      } catch (err) {
        console.error('Error fetching data:', err)
        setError('Failed to load workflows')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Filter workflows based on filter state
  const filteredWorkflows = workflows.filter(workflow => {
    // Name filter
    if (filters.name && !workflow.name.toLowerCase().includes(filters.name.toLowerCase())) {
      return false
    }

    // Integration filter
    if (filters.integration && workflow.integration_id?.toString() !== filters.integration) {
      return false
    }

    // Status filter
    if (filters.status) {
      const isActive = filters.status === 'active'
      if (workflow.active !== isActive) {
        return false
      }
    }

    return true
  })

  // Sort the filtered workflows
  const sortedWorkflows = [...filteredWorkflows].sort((a, b) => {
    if (!sortField) return 0

    let aVal: any = a[sortField as keyof Workflow]
    let bVal: any = b[sortField as keyof Workflow]

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
                    Fetching workflows
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
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                      {/* Step Name Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Step Name</label>
                        <input
                          type="text"
                          placeholder="Filter by step name..."
                          value={filters.stepName}
                          onChange={(e) => setFilters({ ...filters, stepName: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Step # Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Step #</label>
                        <input
                          type="text"
                          placeholder="Filter by step #..."
                          value={filters.stepNumber}
                          onChange={(e) => setFilters({ ...filters, stepNumber: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        />
                      </div>

                      {/* Category Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Category</label>
                        <select
                          value={filters.category}
                          onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Categories</option>
                          <option value="To Do">To Do</option>
                          <option value="In Progress">In Progress</option>
                          <option value="Done">Done</option>
                          <option value="Blocked">Blocked</option>
                        </select>
                      </div>

                      {/* Commitment Point Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Commitment Point</label>
                        <select
                          value={filters.commitmentPoint}
                          onChange={(e) => setFilters({ ...filters, commitmentPoint: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All</option>
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                        </select>
                      </div>

                      {/* Integration Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Integration</label>
                        <select
                          value={filters.integration}
                          onChange={(e) => setFilters({ ...filters, integration: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Integrations</option>
                          {integrations.map(integration => (
                            <option key={integration.id} value={integration.id.toString()}>
                              {integration.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Status Filter */}
                      <div>
                        <label className="block text-sm font-medium mb-2 text-primary">Status</label>
                        <select
                          value={filters.status}
                          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                          className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                        >
                          <option value="">All Statuses</option>
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Workflows Table */}
                  <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
                    {/* Sticky Header Section */}
                    <div className="sticky top-16 z-20 bg-table-container">
                      <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
                        <div className="flex items-center space-x-4">
                          <h2 className="text-lg font-semibold text-table-header">Workflows</h2>
                          {selectedIds.size > 0 && (
                            <span className="text-sm text-secondary">
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
                            onClick={() => {
                              if (integrations.length === 0) {
                                showError('No Integrations Available', 'Please configure at least one data integration before creating workflows.')
                                return
                              }
                              handleCreate()
                            }}
                            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                              <path d="M5 12h14"></path>
                              <path d="M12 5v14"></path>
                            </svg>
                            <span className="text-sm font-medium text-primary">Create Workflow</span>
                          </button>
                        </div>
                    </div>

                      <div className="overflow-x-auto bg-table-column-header">
                        <table className="w-full" style={{ tableLayout: 'fixed' }}>
                          <colgroup>
                            <col style={{ width: '5%' }} />
                            <col style={{ width: '35%' }} />
                            <col style={{ width: '23%' }} />
                            <col style={{ width: '12%' }} />
                            <col style={{ width: '12%' }} />
                            <col style={{ width: '13%' }} />
                          </colgroup>
                          <thead className="bg-table-column-header">
                            <tr className="bg-table-column-header">
                              <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                                <input
                                  type="checkbox"
                                  checked={selectedIds.size === sortedWorkflows.length && sortedWorkflows.length > 0}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedIds(new Set(sortedWorkflows.map(w => w.id)))
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
                              <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">Steps</th>
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
                          <col style={{ width: '35%' }} />
                          <col style={{ width: '23%' }} />
                          <col style={{ width: '12%' }} />
                          <col style={{ width: '12%' }} />
                          <col style={{ width: '13%' }} />
                        </colgroup>
                          <tbody>
                            {sortedWorkflows.length === 0 ? (
                              <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                                <td colSpan={6} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                                  <div className="text-6xl mb-4">⚡</div>
                                  <p className="text-lg mb-2">No workflows found</p>
                                  <p className="text-sm">Try adjusting your filters or create a new workflow</p>
                                </td>
                              </tr>
                            ) : (
                              sortedWorkflows.map((workflow, index) => (
                                <tr
                                  key={workflow.id}
                                  className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!workflow.active ? 'opacity-50' : ''}`}
                                >
                                  <td className="px-6 py-5 whitespace-nowrap text-center">
                                    <input
                                      type="checkbox"
                                      checked={selectedIds.has(workflow.id)}
                                      onChange={(e) => {
                                        const newSelected = new Set(selectedIds)
                                        if (e.target.checked) {
                                          newSelected.add(workflow.id)
                                        } else {
                                          newSelected.delete(workflow.id)
                                        }
                                        setSelectedIds(newSelected)
                                      }}
                                      onClick={(e) => e.stopPropagation()}
                                      className="w-4 h-4 bg-secondary border-gray-400 rounded cursor-pointer"
                                      style={{ accentColor: 'var(--color-1)' }}
                                    />
                                  </td>
                                  <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{workflow.name}</td>
                                  <td className="px-6 py-5 whitespace-nowrap text-center">
                                    <div className="flex items-center justify-center">
                                      <IntegrationLogo
                                        logoFilename={workflow.integration_logo}
                                        integrationName={workflow.integration_name}
                                      />
                                      {!workflow.integration_logo && (
                                        <span className="text-sm text-table-row">
                                          {workflow.integration_name || '-'}
                                        </span>
                                      )}
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div
                                  className="job-toggle-switch cursor-pointer"
                                  onClick={() => handleToggleActive(workflow.id, workflow.active)}
                                >
                                  <div className={`toggle-switch ${workflow.active ? 'active' : ''}`}>
                                    <div className="toggle-slider"></div>
                                  </div>
                                  <span className="toggle-label">{workflow.active ? 'On' : 'Off'}</span>
                                </div>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <button
                                  onClick={() => handleViewSteps(workflow)}
                                  className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md transition-all text-sm font-medium"
                                  title="View Steps"
                                >
                                  View Steps
                                </button>
                              </td>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <div className="flex items-center justify-center space-x-2">
                                  <button
                                    onClick={() => handleEdit(workflow.id)}
                                    className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                                    title="Edit"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                    </svg>
                                  </button>
                                  <button
                                    onClick={() => handleDelete(workflow.id)}
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
                  </div>
              </>
              )}
            </div>

      {/* Dependency Modal */}
      <DependencyModal
        isOpen={dependencyModal.isOpen}
        onClose={() => setDependencyModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={(_targetId) => performToggle(dependencyModal.workflowId!, dependencyModal.action === 'activate')}
        title={`${dependencyModal.action === 'deactivate' ? 'Deactivate' : 'Activate'} Workflow`}
        itemName={dependencyModal.workflowName}
        action={dependencyModal.action}
        dependencyCount={dependencyModal.dependencies.length}
        affectedItemsCount={dependencyModal.dependencies.reduce((sum: number, dep: any) => sum + (dep.affected_items_count || 0), 0)}
        dependencyType="workflow step(s)"
        affectedItemType="work item(s)"
        reassignmentTargets={dependencyModal.reassignmentTargets}
        targetDisplayField="name"
        allowSkipReassignment={dependencyModal.action === 'deactivate'}
        onShowError={showError}
      />

      {/* Workflow Modal (Create/Edit) */}
      <WorkflowModal
        isOpen={workflowModal.isOpen}
        onClose={() => setWorkflowModal({ isOpen: false, workflow: null, existingSteps: [] })}
        onSave={handleWorkflowSave}
        title={workflowModal.workflow ? 'Edit Workflow' : 'Create Workflow'}
        workflow={workflowModal.workflow || undefined}
        existingSteps={workflowModal.existingSteps}
        integrations={integrations}
        statuses={statuses}
      />

      {/* Bulk Edit Modal */}
      <BulkEditModal
        isOpen={bulkEditModal.isOpen}
        onClose={() => setBulkEditModal({ isOpen: false })}
        onSave={handleBulkEditSave}
        title="Bulk Edit Workflows"
        fields={[
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
                    {integrationOptions.map(option => (
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
            label: 'Active',
            type: 'select',
            placeholder: 'Select active status',
            options: [
              { value: 'true', label: '✓ Active' },
              { value: 'false', label: '✗ Inactive' }
            ]
          }
        ]}
      />

      {/* OLD Edit Modal - REMOVE THIS LATER */}
      {false && editModal.workflow && (
        <div style={{display: 'none'}}>
          {/* Keeping for reference, will be removed */}
          fields={[
            {
              name: 'name',
              label: 'Name',
              type: 'text',
              value: editModal.workflow.name,
              required: true,
              placeholder: 'Enter workflow name'
            },
            {
              name: 'integration_id',
              label: 'Integration',
              type: 'select',
              value: editModal.workflow.integration_id || '',
              options: integrations.map(integration => ({
                value: integration.id.toString(),
                label: integration.name
              })),
              customRender: (field: any, formData: any, handleInputChange: any, errors: any) => {
                const selectedIntegrationId = formData[field.name] || field.value
                const selectedIntegration = integrations.find(i => i.id.toString() === selectedIntegrationId?.toString())

                return (
                  <div className="space-y-3">
                    <select
                      id={field.name}
                      value={formData[field.name] || field.value || ''}
                      onChange={(e) => handleInputChange(field.name, e.target.value)}
                      className={`input w-full ${errors[field.name] ? 'border-red-500' : ''}`}
                    >
                      <option value="">Select {field.label}</option>
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
              value: editModal.workflow.active,
              customRender: (field: any, formData: any, handleInputChange: any) => {
                const isActive = formData[field.name] !== undefined ? formData[field.name] : field.value
                return (
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-primary w-24 whitespace-nowrap">Active</label>
                    <div
                      className="job-toggle-switch cursor-pointer"
                      onClick={() => handleInputChange(field.name, !isActive)}
                    >
                      <div className={`toggle-switch ${isActive ? 'active' : ''}`}>
                        <div className="toggle-slider"></div>
                      </div>
                      <span className="toggle-label">{isActive ? 'On' : 'Off'}</span>
                    </div>
                  </div>
                )
              }
            }
          ]}
        </div>
      )}

      {/* Workflow Steps Modal */}
      {stepsModal.isOpen && stepsModal.workflow && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-primary rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-primary">Workflow Steps</h2>
                <p className="text-sm text-secondary mt-1">
                  Steps for workflow: <span className="font-semibold">{stepsModal.workflow.name}</span>
                </p>
              </div>
              <button
                onClick={() => setStepsModal({ isOpen: false, workflow: null, steps: [] })}
                className="p-2 rounded-lg hover:bg-secondary transition-colors"
                title="Close"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-auto p-6">
              {stepsModal.steps.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">⚡</div>
                  <p className="text-lg mb-2 text-primary">No steps found</p>
                  <p className="text-sm text-secondary">This workflow doesn't have any steps yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-table-column-header">
                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Step Name
                        </th>
                        <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Order
                        </th>
                        <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Status
                        </th>
                        <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Commitment Point
                        </th>
                        <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Active
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {stepsModal.steps.map((step, index) => (
                        <tr
                          key={step.id}
                          className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!step.active ? 'opacity-50' : ''}`}
                        >
                          <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">
                            {step.name}
                          </td>
                          <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">
                            {step.order || '-'}
                          </td>
                          <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">
                            {step.status_name || '-'}
                          </td>
                          <td className="px-6 py-5 whitespace-nowrap text-center">
                            <div className="job-toggle-switch">
                              <div className={`toggle-switch ${step.is_commitment_point ? 'active' : ''}`}>
                                <div className="toggle-slider"></div>
                              </div>
                              <span className="toggle-label">{step.is_commitment_point ? 'Yes' : 'No'}</span>
                            </div>
                          </td>
                          <td className="px-6 py-5 whitespace-nowrap text-center">
                            <div className="job-toggle-switch">
                              <div className={`toggle-switch ${step.active ? 'active' : ''}`}>
                                <div className="toggle-slider"></div>
                              </div>
                              <span className="toggle-label">{step.active ? 'On' : 'Off'}</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                onClick={() => setStepsModal({ isOpen: false, workflow: null, steps: [] })}
                className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

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

export default WorkflowsPage
