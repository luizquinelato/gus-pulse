import React, { useState, useEffect } from 'react'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import Header from '../components/Header'
import CollapsedSidebar from '../components/CollapsedSidebar'
import DependencyModal from '../components/DependencyModal'
import ConfirmationModal from '../components/ConfirmationModal'
import EditModal from '../components/EditModal'
import CreateModal from '../components/CreateModal'
import ToastContainer from '../components/ToastContainer'
import IntegrationLogo from '../components/IntegrationLogo'
import { useToast } from '../hooks/useToast'
import { useConfirmation } from '../hooks/useConfirmation'
import { statusesApi, integrationsApi } from '../services/etlApiService'

interface WorkflowStep {
  id: number
  workflow_id: number
  workflow_name?: string
  step_name: string
  step_number?: number
  step_category: string
  status_mapping_id: number
  status_to?: string
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

interface WorkflowsStepsPageProps {
  embedded?: boolean
}

const WorkflowsStepsPage: React.FC<WorkflowsStepsPageProps> = ({ embedded = false }) => {
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toasts, removeToast, showSuccess, showError } = useToast()
  const { confirmation, confirmDelete, hideConfirmation } = useConfirmation()

  // Filter states
  const [filters, setFilters] = useState({
    workflowName: '',
    stepName: '',
    stepNumber: '',
    category: '',
    statusTo: '',
    commitmentPoint: '',
    integration: '',
    status: ''
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

  // Edit modal state
  const [editModal, setEditModal] = useState({
    isOpen: false,
    workflowStep: null as WorkflowStep | null
  })

  // Create modal state
  const [createModal, setCreateModal] = useState({
    isOpen: false
  })

  // Dependency modal state
  const [dependencyModal, setDependencyModal] = useState({
    isOpen: false,
    workflowStepId: null as number | null,
    workflowStepName: '',
    action: 'deactivate' as 'deactivate' | 'activate',
    dependencies: [] as any[],
    reassignmentTargets: [] as any[]
  })

  // Handler functions
  const checkDependencies = async (workflowStepId: number): Promise<any> => {
    try {
      // TODO: Implement actual dependency checking API call
      return {
        has_dependencies: Math.random() > 0.7,
        dependency_count: Math.floor(Math.random() * 3) + 1,
        affected_items_count: Math.floor(Math.random() * 10) + 1,
        reassignment_targets: workflowSteps.filter(w => w.id !== workflowStepId && w.active).slice(0, 3)
      }
    } catch (error) {
      console.error('Error checking dependencies:', error)
      return { has_dependencies: false }
    }
  }

  const handleToggleActive = async (workflowStepId: number, currentActive: boolean) => {
    const workflowStep = workflowSteps.find(w => w.id === workflowStepId)
    if (!workflowStep) return

    const action = currentActive ? 'deactivate' : 'activate'

    // Check for dependencies
    const depCheck = await checkDependencies(workflowStepId)

    if (depCheck.has_dependencies) {
      setDependencyModal({
        isOpen: true,
        workflowStepId,
        workflowStepName: workflowStep.step_name,
        action,
        dependencies: depCheck.dependencies || [],
        reassignmentTargets: depCheck.reassignment_targets || []
      })
    } else {
      // No dependencies, proceed with toggle
      await performToggleActive(workflowStepId, !currentActive)
    }
  }

  const performToggleActive = async (workflowStepId: number, newActiveState: boolean, reassignmentId?: number) => {
    try {
      // TODO: Implement actual API call
      // await statusesApi.updateWorkflowStep(workflowStepId, { active: newActiveState, reassignment_id: reassignmentId })

      // Update local state
      setWorkflowSteps(prev => prev.map(w =>
        w.id === workflowStepId ? { ...w, active: newActiveState } : w
      ))

      showSuccess(
        'Status Updated',
        `Workflow step has been ${newActiveState ? 'activated' : 'deactivated'} successfully.`
      )
    } catch (error) {
      console.error('Error toggling active status:', error)
      showError('Update Failed', 'Failed to update workflow step status. Please try again.')
    }
  }

  const handleDependencyResolve = async (reassignmentId?: number) => {
    if (dependencyModal.workflowStepId) {
      const newActiveState = dependencyModal.action === 'activate'
      await performToggleActive(dependencyModal.workflowStepId, newActiveState, reassignmentId)
      setDependencyModal({ ...dependencyModal, isOpen: false })
    }
  }

  // Handle edit
  const handleEdit = (workflowStepId: number) => {
    const workflowStep = workflowSteps.find(w => w.id === workflowStepId)
    if (workflowStep) {
      setEditModal({ isOpen: true, workflowStep })
    }
  }

  // Handle edit save
  const handleEditSave = async (formData: Record<string, any>) => {
    if (!editModal.workflowStep) return

    try {
      const updateData = {
        workflow_id: formData.workflow_id ? parseInt(formData.workflow_id) : null,
        step_name: formData.step_name,
        step_number: formData.step_number ? parseInt(formData.step_number) : null,
        step_category: formData.step_category,
        status_mapping_id: formData.status_mapping_id ? parseInt(formData.status_mapping_id) : null,
        is_commitment_point: formData.is_commitment_point === 'true' || formData.is_commitment_point === true,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null
      }

      // TODO: Implement actual API call
      // const response = await statusesApi.updateWorkflowStep(editModal.workflowStep.id, updateData)

      // Update local state
      setWorkflowSteps(prev => prev.map(w =>
        w.id === editModal.workflowStep!.id ? { ...w, ...updateData } : w
      ))

      showSuccess('Workflow Step Updated', 'The workflow step has been updated successfully.')
      setEditModal({ isOpen: false, workflowStep: null })
    } catch (error) {
      console.error('Error updating workflow step:', error)
      showError('Update Failed', 'Failed to update workflow step. Please try again.')
    }
  }

  // Handle create save
  const handleCreateSave = async (formData: Record<string, any>) => {
    try {
      const createData = {
        workflow_id: formData.workflow_id ? parseInt(formData.workflow_id) : null,
        step_name: formData.step_name,
        step_number: formData.step_number ? parseInt(formData.step_number) : null,
        step_category: formData.step_category,
        status_mapping_id: formData.status_mapping_id ? parseInt(formData.status_mapping_id) : null,
        is_commitment_point: formData.is_commitment_point === 'true' || formData.is_commitment_point === true,
        integration_id: formData.integration_id ? parseInt(formData.integration_id) : null
      }

      // TODO: Implement actual API call
      // const response = await statusesApi.createWorkflowStep(createData)

      // Add new workflow step to local state
      const newWorkflowStep = {
        id: Math.max(...workflowSteps.map(w => w.id), 0) + 1,
        ...createData,
        active: true
      }

      setWorkflowSteps(prev => [...prev, newWorkflowStep])

      showSuccess('Workflow Step Created', 'The workflow step has been created successfully.')
      setCreateModal({ isOpen: false })
    } catch (error) {
      console.error('Error creating workflow step:', error)
      showError('Create Failed', 'Failed to create workflow step. Please try again.')
    }
  }

  // Handle delete
  const handleDelete = async (workflowStepId: number) => {
    const workflowStep = workflowSteps.find(w => w.id === workflowStepId)
    if (!workflowStep) return

    confirmDelete(
      workflowStep.step_name,
      async () => {
        try {
          // TODO: Implement actual API call
          // await statusesApi.deleteWorkflowStep(workflowStepId)

          // Remove from local state
          setWorkflowSteps(prev => prev.filter(w => w.id !== workflowStepId))

          showSuccess('Workflow Step Deleted', 'The workflow step has been deleted successfully.')
        } catch (error) {
          console.error('Error deleting workflow step:', error)
          showError('Delete Failed', 'Failed to delete workflow step. Please try again.')
        }
      }
    )
  }

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch integrations
        const integrationsResponse = await integrationsApi.getIntegrations()
        setIntegrations(integrationsResponse.data || [])

        // TODO: Implement actual API call for workflow steps
        // const workflowStepsResponse = await statusesApi.getWorkflowSteps()
        // setWorkflowSteps(workflowStepsResponse.data || [])

        // Mock data for now
        setWorkflowSteps([])

      } catch (err) {
        console.error('Error fetching data:', err)
        setError('Failed to load workflow steps. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Filtered workflow steps based on filter states
  const filteredWorkflowSteps = workflowSteps.filter(step => {
    const matchesWorkflowName = !filters.workflowName ||
      (step.workflow_name && step.workflow_name.toLowerCase().includes(filters.workflowName.toLowerCase()))
    const matchesStepName = !filters.stepName ||
      step.step_name.toLowerCase().includes(filters.stepName.toLowerCase())
    const matchesStepNumber = !filters.stepNumber ||
      (step.step_number && step.step_number.toString().includes(filters.stepNumber))
    const matchesCategory = !filters.category ||
      step.step_category.toLowerCase().includes(filters.category.toLowerCase())
    const matchesStatusTo = !filters.statusTo ||
      (step.status_to && step.status_to.toLowerCase().includes(filters.statusTo.toLowerCase()))
    const matchesCommitmentPoint = !filters.commitmentPoint ||
      (filters.commitmentPoint === 'yes' && step.is_commitment_point) ||
      (filters.commitmentPoint === 'no' && !step.is_commitment_point)
    const matchesIntegration = !filters.integration ||
      (step.integration_name && step.integration_name.toLowerCase().includes(filters.integration.toLowerCase()))
    const matchesStatus = !filters.status ||
      (filters.status === 'active' && step.active) ||
      (filters.status === 'inactive' && !step.active)

    return matchesWorkflowName && matchesStepName && matchesStepNumber && matchesCategory &&
           matchesStatusTo && matchesCommitmentPoint && matchesIntegration && matchesStatus
  })

  // Sorted workflow steps
  const sortedWorkflowSteps = [...filteredWorkflowSteps].sort((a, b) => {
    if (!sortField) return 0

    let aValue: any = a[sortField as keyof WorkflowStep]
    let bValue: any = b[sortField as keyof WorkflowStep]

    // Handle null/undefined values
    if (aValue === null || aValue === undefined) return 1
    if (bValue === null || bValue === undefined) return -1

    // Convert to strings for comparison
    aValue = String(aValue).toLowerCase()
    bValue = String(bValue).toLowerCase()

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
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
              Fetching workflow steps
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
            <div
              className="bg-secondary rounded-lg shadow-sm p-6 mb-6 border border-gray-400"
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-1)'
                e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#9ca3af'
                e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
              }}
            >
              <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
                {/* Workflow Name Filter */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-primary">Workflow</label>
                  <input
                    type="text"
                    placeholder="Filter by workflow..."
                    value={filters.workflowName}
                    onChange={(e) => setFilters({ ...filters, workflowName: e.target.value })}
                    className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                  />
                </div>

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

                {/* Status Filter */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-primary">Status</label>
                  <input
                    type="text"
                    placeholder="Filter by status..."
                    value={filters.statusTo}
                    onChange={(e) => setFilters({ ...filters, statusTo: e.target.value })}
                    className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                  />
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
                    <option value="GitHub">GitHub</option>
                    <option value="Jira">Jira</option>
                  </select>
                </div>

                {/* Category Filter */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-primary">Category</label>
                  <input
                    type="text"
                    placeholder="Filter by category..."
                    value={filters.category}
                    onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                    className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary"
                  />
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

                {/* Active Status Filter */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-primary">Active Status</label>
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


            {/* Workflow Steps Table */}
            <div className="rounded-lg bg-table-container shadow-md overflow-hidden border border-gray-400">
              <div className="px-6 py-5 flex justify-between items-center bg-table-header">
                <h2 className="text-lg font-semibold text-table-header">Workflow Steps</h2>
                <button
                  onClick={() => {
                    if (integrations.length === 0) {
                      showError('No Integrations Available', 'Please configure at least one data integration before creating workflow steps.')
                      return
                    }
                    setCreateModal({ isOpen: true })
                  }}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 font-medium shadow-sm"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14"></path>
                    <path d="M12 5v14"></path>
                  </svg>
                  <span>Create Workflow Step</span>
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-table-column-header">
                      <th
                        className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('workflow_name')}
                      >
                        <div className="flex items-center gap-2">
                          Workflow
                          {sortField === 'workflow_name' ? (
                            sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                          ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                          )}
                        </div>
                      </th>
                      <th
                        className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('step_name')}
                      >
                        <div className="flex items-center gap-2">
                          Step Name
                          {sortField === 'step_name' ? (
                            sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                          ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                          )}
                        </div>
                      </th>
                      <th
                        className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('step_number')}
                      >
                        <div className="flex items-center justify-center gap-2">
                          Step #
                          {sortField === 'step_number' ? (
                            sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                          ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                          )}
                        </div>
                      </th>
                      <th
                        className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('status_to')}
                      >
                        <div className="flex items-center justify-center gap-2">
                          Status
                          {sortField === 'status_to' ? (
                            sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                          ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                          )}
                        </div>
                      </th>
                      <th
                        className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('step_category')}
                      >
                        <div className="flex items-center justify-center gap-2">
                          Category
                          {sortField === 'step_category' ? (
                            sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
                          ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                          )}
                        </div>
                      </th>
                      <th
                        className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header cursor-pointer hover:bg-opacity-80"
                        onClick={() => handleSort('is_commitment_point')}
                      >
                        <div className="flex items-center justify-center gap-2">
                          Commitment Point
                          {sortField === 'is_commitment_point' ? (
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
                  <tbody>
                    {sortedWorkflowSteps.length === 0 ? (
                      <tr className="!bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                        <td colSpan={9} className="px-6 py-12 text-center text-secondary !bg-[#f9fafb] dark:!bg-[#1e1e1e]">
                          <div className="text-6xl mb-4">⚡</div>
                          <p className="text-lg mb-2">No workflow steps found</p>
                          <p className="text-sm">Try adjusting your filters or create a new workflow step</p>
                        </td>
                      </tr>
                    ) : (
                      sortedWorkflowSteps.map((step, index) => (
                        <tr
                          key={step.id}
                          className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'} ${!step.active ? 'opacity-50' : ''}`}
                        >
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{step.workflow_name || '-'}</td>
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-table-row font-semibold">{step.step_name}</td>
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">{step.step_number || '-'}</td>
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">{step.status_to || '-'}</td>
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">{step.step_category}</td>
                        <td className="px-6 py-5 whitespace-nowrap text-sm text-center text-table-row">
                          {step.is_commitment_point ? (
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">Yes</span>
                          ) : (
                            <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-full text-xs font-medium">No</span>
                          )}
                        </td>
                        <td className="px-6 py-5 whitespace-nowrap text-center">
                          <div className="flex items-center justify-center">
                            <IntegrationLogo
                              logoFilename={step.integration_logo}
                              integrationName={step.integration_name}
                            />
                            {!step.integration_logo && (
                              <span className="text-sm text-table-row">
                                {step.integration_name || '-'}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-5 whitespace-nowrap text-center">
                          <div
                            className="job-toggle-switch cursor-pointer"
                            onClick={() => handleToggleActive(step.id, step.active)}
                          >
                            <div className={`toggle-switch ${step.active ? 'active' : ''}`}>
                              <div className="toggle-slider"></div>
                            </div>
                            <span className="toggle-label">{step.active ? 'On' : 'Off'}</span>
                          </div>
                        </td>
                        <td className="px-6 py-5 whitespace-nowrap text-center">
                          <div className="flex items-center justify-center space-x-2">
                            <button
                              onClick={() => handleEdit(step.id)}
                              className="p-2 rounded bg-tertiary text-secondary hover:bg-secondary hover:text-accent shadow-sm hover:shadow-md transition-all"
                              title="Edit"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                              </svg>
                            </button>
                            <button
                              onClick={() => handleDelete(step.id)}
                              className="p-2 rounded bg-red-100 text-red-600 hover:bg-red-200 shadow-sm hover:shadow-md transition-all"
                              title="Delete"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M3 6h18"></path>
                                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
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

      {/* Modals */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
      <ConfirmationModal {...confirmation} onCancel={hideConfirmation} />
      <DependencyModal
        isOpen={dependencyModal.isOpen}
        onClose={() => setDependencyModal({ ...dependencyModal, isOpen: false })}
        onResolve={handleDependencyResolve}
        itemName={dependencyModal.workflowStepName}
        action={dependencyModal.action}
        dependencies={dependencyModal.dependencies}
        reassignmentTargets={dependencyModal.reassignmentTargets}
      />

      {/* Edit Modal - TODO: Add proper fields */}
      {editModal.isOpen && editModal.workflowStep && (
        <EditModal
          isOpen={editModal.isOpen}
          onClose={() => setEditModal({ isOpen: false, workflowStep: null })}
          onSave={handleEditSave}
          title="Edit Workflow Step"
          fields={[
            {
              name: 'step_name',
              label: 'Step Name',
              type: 'text',
              value: editModal.workflowStep.step_name,
              required: true,
              placeholder: 'Enter step name'
            },
            {
              name: 'step_number',
              label: 'Step Number',
              type: 'number',
              value: editModal.workflowStep.step_number || '',
              placeholder: 'Enter step number'
            },
            {
              name: 'step_category',
              label: 'Category',
              type: 'text',
              value: editModal.workflowStep.step_category,
              required: true,
              placeholder: 'Enter category'
            },
            {
              name: 'is_commitment_point',
              label: 'Commitment Point',
              type: 'select',
              value: editModal.workflowStep.is_commitment_point ? 'true' : 'false',
              required: true,
              options: [
                { value: 'true', label: 'Yes' },
                { value: 'false', label: 'No' }
              ]
            }
          ]}
        />
      )}

      {/* Create Modal - TODO: Add proper fields */}
      <CreateModal
        isOpen={createModal.isOpen}
        onClose={() => setCreateModal({ isOpen: false })}
        onSave={handleCreateSave}
        title="Create Workflow Step"
        fields={[
          {
            name: 'step_name',
            label: 'Step Name',
            type: 'text',
            required: true,
            placeholder: 'Enter step name'
          },
          {
            name: 'step_number',
            label: 'Step Number',
            type: 'number',
            placeholder: 'Enter step number'
          },
          {
            name: 'step_category',
            label: 'Category',
            type: 'text',
            required: true,
            placeholder: 'Enter category'
          },
          {
            name: 'is_commitment_point',
            label: 'Commitment Point',
            type: 'select',
            required: true,
            defaultValue: 'false',
            options: [
              { value: 'true', label: 'Yes' },
              { value: 'false', label: 'No' }
            ]
          }
        ]}
      />
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

export default WorkflowsStepsPage
