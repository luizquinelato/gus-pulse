import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X, Plus, Trash2, GripVertical, ChevronsUp, ChevronsDown } from 'lucide-react'

interface WorkflowStep {
  id?: number
  name: string
  order: number
  status_id?: number
  status_name?: string
  is_commitment_point: boolean
  active: boolean
  _isNew?: boolean
  _isDeleted?: boolean
}

interface Integration {
  id: number
  name: string
  logo_filename?: string
}

interface Status {
  id: number
  name: string
  original_name?: string
}

interface WorkflowModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (workflowData: any, steps: WorkflowStep[]) => Promise<void>
  title: string
  workflow?: {
    id?: number
    name: string
    integration_id?: number
    integration_name?: string
    integration_logo?: string
    active: boolean
  }
  existingSteps?: WorkflowStep[]
  integrations: Integration[]
  statuses: Status[]
}

export default function WorkflowModal({
  isOpen,
  onClose,
  onSave,
  title,
  workflow,
  existingSteps = [],
  integrations,
  statuses
}: WorkflowModalProps) {
  const [workflowName, setWorkflowName] = useState('')
  const [integrationId, setIntegrationId] = useState<number | undefined>(undefined)
  const [active, setActive] = useState(true)
  const [steps, setSteps] = useState<WorkflowStep[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [selectedStepIndices, setSelectedStepIndices] = useState<Set<number>>(new Set())

  // Initialize form data when modal opens
  useEffect(() => {
    if (isOpen) {
      if (workflow) {
        setWorkflowName(workflow.name)
        setIntegrationId(workflow.integration_id)
        setActive(workflow.active)
        setSteps(existingSteps.map(step => ({ ...step })))
      } else {
        setWorkflowName('')
        setIntegrationId(integrations.length > 0 ? integrations[0].id : undefined)
        setActive(true)
        setSteps([])
      }
      setErrors({})
      setSelectedStepIndices(new Set())
    }
  }, [isOpen, workflow, existingSteps, integrations])

  const handleAddStep = () => {
    const newStep: WorkflowStep = {
      name: '',
      order: steps.length + 1,
      status_id: undefined,
      is_commitment_point: false,
      active: true,
      _isNew: true
    }
    setSteps([...steps, newStep])
  }

  // Toggle individual step selection
  const handleToggleStepSelection = (index: number) => {
    const newSelected = new Set(selectedStepIndices)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedStepIndices(newSelected)
  }

  // Toggle all steps selection
  const handleToggleAllSteps = () => {
    const visibleIndices = steps
      .map((step, index) => (!step._isDeleted ? index : -1))
      .filter(index => index !== -1)

    if (selectedStepIndices.size === visibleIndices.length) {
      setSelectedStepIndices(new Set())
    } else {
      setSelectedStepIndices(new Set(visibleIndices))
    }
  }

  // Bulk delete selected steps
  const handleBulkDeleteSteps = () => {
    const updatedSteps = steps.map((step, index) => {
      if (selectedStepIndices.has(index)) {
        return { ...step, _isDeleted: true }
      }
      return step
    })
    setSteps(updatedSteps)
    setSelectedStepIndices(new Set())
  }

  const handleRemoveStep = (index: number) => {
    const updatedSteps = [...steps]
    if (updatedSteps[index].id) {
      // Mark existing step as deleted
      updatedSteps[index]._isDeleted = true
    } else {
      // Remove new step completely
      updatedSteps.splice(index, 1)
    }
    setSteps(updatedSteps)
  }

  const handleStepChange = (index: number, field: keyof WorkflowStep, value: any) => {
    const updatedSteps = [...steps]

    // Special handling for commitment point toggle
    if (field === 'is_commitment_point' && value === true) {
      // Check if another step already has commitment point
      const existingCommitmentIndex = updatedSteps.findIndex(
        (s, i) => i !== index && s.is_commitment_point && !s._isDeleted
      )

      if (existingCommitmentIndex !== -1) {
        // Turn off the existing commitment point
        updatedSteps[existingCommitmentIndex] = {
          ...updatedSteps[existingCommitmentIndex],
          is_commitment_point: false
        }
      }
    }

    updatedSteps[index] = { ...updatedSteps[index], [field]: value }
    setSteps(updatedSteps)
  }

  const handleMoveToTop = (index: number) => {
    if (index === 0) return
    const updatedSteps = [...steps]
    const [movedStep] = updatedSteps.splice(index, 1)
    updatedSteps.unshift(movedStep)
    // Update order numbers
    updatedSteps.forEach((step, idx) => {
      step.order = idx + 1
    })
    setSteps(updatedSteps)
  }

  const handleMoveToBottom = (index: number) => {
    if (index === steps.length - 1) return
    const updatedSteps = [...steps]
    const [movedStep] = updatedSteps.splice(index, 1)
    updatedSteps.push(movedStep)
    // Update order numbers
    updatedSteps.forEach((step, idx) => {
      step.order = idx + 1
    })
    setSteps(updatedSteps)
  }

  const handleDragStart = (index: number) => {
    setDraggedIndex(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (draggedIndex === null || draggedIndex === index) return

    const updatedSteps = [...steps]
    const draggedStep = updatedSteps[draggedIndex]
    updatedSteps.splice(draggedIndex, 1)
    updatedSteps.splice(index, 0, draggedStep)

    // Update order numbers
    updatedSteps.forEach((step, idx) => {
      step.order = idx + 1
    })

    setSteps(updatedSteps)
    setDraggedIndex(index)
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!workflowName.trim()) {
      newErrors.name = 'Workflow name is required'
    }

    // Validate steps
    steps.forEach((step, index) => {
      if (!step._isDeleted && !step.name.trim()) {
        newErrors[`step_${index}_name`] = 'Step name is required'
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    if (!validateForm()) return

    try {
      setSaving(true)
      const workflowData = {
        name: workflowName,
        integration_id: integrationId,
        active
      }
      
      // Filter out deleted steps
      const validSteps = steps.filter(step => !step._isDeleted)
      
      await onSave(workflowData, validSteps)
      onClose()
    } catch (error) {
      console.error('Error saving workflow:', error)
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  const selectedIntegration = integrations.find(i => i.id === integrationId)
  const visibleSteps = steps.filter(step => !step._isDeleted)

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative min-h-screen flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative bg-primary rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-primary">{title}</h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-secondary transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Workflow Details Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-primary border-b border-gray-200 dark:border-gray-700 pb-2">
                Workflow Details
              </h3>

              {/* Workflow Name */}
              <div>
                <label htmlFor="workflow-name" className="block text-sm font-medium text-primary mb-2">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  id="workflow-name"
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className={`input w-full ${errors.name ? 'border-red-500' : ''}`}
                  placeholder="Enter workflow name"
                />
                {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
              </div>

              {/* Integration */}
              <div>
                <label htmlFor="integration" className="block text-sm font-medium text-primary mb-2">
                  Integration
                </label>
                <select
                  id="integration"
                  value={integrationId || ''}
                  onChange={(e) => setIntegrationId(e.target.value ? parseInt(e.target.value) : undefined)}
                  className="input w-full"
                >
                  <option value="">- No Integration -</option>
                  {integrations.map((integration) => (
                    <option key={integration.id} value={integration.id}>
                      {integration.name}
                    </option>
                  ))}
                </select>
                {selectedIntegration && (
                  <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg mt-3">
                    {selectedIntegration.logo_filename ? (
                      <img
                        src={`/assets/integrations/${selectedIntegration.logo_filename}`}
                        alt={selectedIntegration.name}
                        className="h-8 w-8 object-contain"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                    ) : (
                      <div className="h-8 w-8 bg-blue-100 dark:bg-blue-800 rounded-lg flex items-center justify-center">
                        <span className="text-sm text-blue-600 dark:text-blue-300 font-semibold">
                          {selectedIntegration.name.charAt(0)}
                        </span>
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedIntegration.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Integration Provider</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Active Toggle */}
              {workflow && (
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-primary w-24 whitespace-nowrap">Active</label>
                  <div
                    className="job-toggle-switch cursor-pointer"
                    onClick={() => setActive(!active)}
                  >
                    <div className={`toggle-switch ${active ? 'active' : ''}`}>
                      <div className="toggle-slider"></div>
                    </div>
                    <span className="toggle-label">{active ? 'On' : 'Off'}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Workflow Steps Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-2">
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-semibold text-primary">
                    Workflow Steps
                    <span className="text-sm text-secondary ml-2">({visibleSteps.length})</span>
                  </h3>
                  {visibleSteps.length > 0 && selectedStepIndices.size > 0 && (
                    <span className="text-sm text-secondary">
                      ({selectedStepIndices.size} selected)
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {selectedStepIndices.size > 0 && (
                    <button
                      onClick={handleBulkDeleteSteps}
                      className="flex items-center gap-2 px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700 transition-colors text-sm font-medium"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Selected ({selectedStepIndices.size})
                    </button>
                  )}
                  <button
                    onClick={handleAddStep}
                    className="flex items-center gap-2 px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors text-sm font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Add Step
                  </button>
                </div>
              </div>

              {/* Steps List */}
              {visibleSteps.length === 0 ? (
                <div className="text-center py-8 bg-secondary rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
                  <p className="text-secondary">No steps added yet</p>
                  <p className="text-sm text-secondary mt-1">Click "Add Step" to create workflow steps</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Select All Header */}
                  <div className="flex items-center gap-3 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg mb-2">
                    {/* Checkbox */}
                    <input
                      type="checkbox"
                      checked={visibleSteps.length > 0 && selectedStepIndices.size === visibleSteps.length}
                      onChange={handleToggleAllSteps}
                      className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent cursor-pointer"
                      style={{ accentColor: 'var(--color-1)' }}
                    />

                    {/* Select All Label */}
                    <span className="text-sm font-medium text-secondary">
                      All
                    </span>

                    {/* Drag Handle & Order Placeholder */}
                    <div className="flex items-center gap-2 text-secondary">
                      <GripVertical className="w-5 h-5 invisible" />
                      <span className="text-sm font-semibold min-w-[2rem] invisible">#1</span>
                    </div>

                    {/* Step Name Header - Empty */}
                    <div className="flex-1"></div>

                    {/* Status Header - Empty */}
                    <div className="flex-1"></div>

                    {/* Commitment Point Placeholder */}
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-medium text-secondary whitespace-nowrap invisible">
                        Commitment
                      </label>
                      <div className="job-toggle-switch scale-75 invisible">
                        <div className="toggle-switch">
                          <div className="toggle-slider"></div>
                        </div>
                      </div>
                    </div>

                    {/* Active Placeholder */}
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-medium text-secondary whitespace-nowrap invisible">
                        Active
                      </label>
                      <div className="job-toggle-switch scale-75 invisible">
                        <div className="toggle-switch">
                          <div className="toggle-slider"></div>
                        </div>
                      </div>
                    </div>

                    {/* Delete Button Placeholder */}
                    <button className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors invisible">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {steps.map((step, index) => {
                    if (step._isDeleted) return null

                    return (
                      <div
                        key={index}
                        draggable
                        onDragStart={() => handleDragStart(index)}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragEnd={handleDragEnd}
                        className={`bg-secondary border border-gray-200 dark:border-gray-700 rounded-lg p-3 transition-all ${
                          draggedIndex === index ? 'opacity-50' : 'opacity-100'
                        } hover:border-blue-400 dark:hover:border-blue-600 cursor-move`}
                      >
                        <div className="flex items-center gap-3">
                          {/* Checkbox */}
                          <input
                            type="checkbox"
                            checked={selectedStepIndices.has(index)}
                            onChange={() => handleToggleStepSelection(index)}
                            onClick={(e) => e.stopPropagation()}
                            className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent cursor-pointer"
                            style={{ accentColor: 'var(--color-1)' }}
                          />

                          {/* Drag Handle & Order */}
                          <div className="flex items-center gap-2 text-secondary">
                            <GripVertical className="w-5 h-5 cursor-grab active:cursor-grabbing" />
                            <span className="text-sm font-semibold min-w-[2rem]">#{step.order}</span>
                          </div>

                          {/* Step Name */}
                          <div className="flex-1">
                            <input
                              type="text"
                              value={step.name}
                              onChange={(e) => handleStepChange(index, 'name', e.target.value)}
                              className={`input w-full text-sm ${errors[`step_${index}_name`] ? 'border-red-500' : ''}`}
                              placeholder="Step name *"
                            />
                            {errors[`step_${index}_name`] && (
                              <p className="text-red-500 text-xs mt-0.5">{errors[`step_${index}_name`]}</p>
                            )}
                          </div>

                          {/* Status */}
                          <div className="flex-1">
                            <select
                              value={step.status_id || ''}
                              onChange={(e) => handleStepChange(index, 'status_id', e.target.value ? parseInt(e.target.value) : undefined)}
                              className="input w-full text-sm"
                            >
                              <option value="">Select Status</option>
                              {[...statuses]
                                .sort((a, b) => {
                                  // Sort by name first
                                  const nameCompare = a.name.localeCompare(b.name)
                                  if (nameCompare !== 0) return nameCompare
                                  // Then by original_name
                                  const aOriginal = a.original_name || ''
                                  const bOriginal = b.original_name || ''
                                  return aOriginal.localeCompare(bOriginal)
                                })
                                .map((status) => (
                                  <option key={status.id} value={status.id}>
                                    {status.name}{status.original_name ? ` (${status.original_name})` : ''}
                                  </option>
                                ))}
                            </select>
                          </div>

                          {/* Commitment Point Toggle */}
                          <div className="flex items-center gap-2">
                            <label className="text-xs font-medium text-secondary whitespace-nowrap">
                              Commitment
                            </label>
                            <div
                              className="job-toggle-switch cursor-pointer scale-75"
                              onClick={() => handleStepChange(index, 'is_commitment_point', !step.is_commitment_point)}
                            >
                              <div className={`toggle-switch ${step.is_commitment_point ? 'active' : ''}`}>
                                <div className="toggle-slider"></div>
                              </div>
                              <span className="toggle-label text-xs">{step.is_commitment_point ? 'Yes' : 'No'}</span>
                            </div>
                          </div>

                          {/* Active Toggle */}
                          <div className="flex items-center gap-2">
                            <label className="text-xs font-medium text-secondary whitespace-nowrap">
                              Active
                            </label>
                            <div
                              className="job-toggle-switch cursor-pointer scale-75"
                              onClick={() => handleStepChange(index, 'active', !step.active)}
                            >
                              <div className={`toggle-switch ${step.active ? 'active' : ''}`}>
                                <div className="toggle-slider"></div>
                              </div>
                              <span className="toggle-label text-xs">{step.active ? 'On' : 'Off'}</span>
                            </div>
                          </div>

                          {/* Move to Top/Bottom Buttons */}
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleMoveToTop(index)}
                              disabled={index === 0}
                              className="p-1.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900/20 text-blue-600 dark:text-blue-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                              title="Move to top"
                            >
                              <ChevronsUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleMoveToBottom(index)}
                              disabled={index === steps.filter(s => !s._isDeleted).length - 1}
                              className="p-1.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900/20 text-blue-600 dark:text-blue-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                              title="Move to bottom"
                            >
                              <ChevronsDown className="w-4 h-4" />
                            </button>
                          </div>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleRemoveStep(index)}
                            className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-colors"
                            title="Remove step"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Workflow'
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

