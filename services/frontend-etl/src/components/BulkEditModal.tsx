import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X } from 'lucide-react'

interface BulkEditField {
  name: string
  label: string
  type: 'select' | 'text' | 'checkbox'
  options?: { value: any; label: string }[]
  placeholder?: string
  customRender?: (
    field: BulkEditField,
    formData: Record<string, any>,
    handleInputChange: (name: string, value: any) => void
  ) => React.ReactNode
}

interface BulkEditModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: Record<string, any>) => Promise<void>
  title: string
  selectedCount: number
  fields: BulkEditField[]
}

export default function BulkEditModal({
  isOpen,
  onClose,
  onSave,
  title,
  selectedCount,
  fields
}: BulkEditModalProps) {
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)

  // Initialize form data when modal opens
  useEffect(() => {
    if (isOpen) {
      const initialData: Record<string, any> = {}
      fields.forEach(field => {
        initialData[field.name] = '' // Empty by default for bulk edit
      })
      setFormData(initialData)
    }
  }, [isOpen, fields])

  const handleInputChange = (name: string, value: any) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    // Filter out empty values - only update fields that were changed
    const changedData = Object.entries(formData).reduce((acc, [key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        acc[key] = value
      }
      return acc
    }, {} as Record<string, any>)

    // Check if at least one field was changed
    if (Object.keys(changedData).length === 0) {
      return
    }

    try {
      setSaving(true)
      await onSave(changedData)
      onClose()
    } catch (error) {
      console.error('Error saving:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSave()
    }
  }

  if (!isOpen) return null

  // Check if any field has been changed
  const hasChanges = Object.values(formData).some(value => value !== '' && value !== null && value !== undefined)

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl bg-primary rounded-xl shadow-2xl border border-tertiary overflow-hidden"
          onKeyDown={handleKeyDown}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 bg-table-header border-b border-tertiary">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-table-header">{title}</h3>
                <p className="text-sm text-white/70 mt-0.5">
                  Editing {selectedCount} {selectedCount === 1 ? 'item' : 'items'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-secondary hover:bg-tertiary hover:text-primary transition-colors"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-8 space-y-6 max-h-[70vh] overflow-y-auto bg-secondary">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>Note:</strong> Only fields you change will be updated. Leave fields empty to keep their current values.
              </p>
            </div>

            {fields.map((field) => (
              <div key={field.name} className="space-y-3">
                <label className="block text-sm font-semibold text-primary">
                  {field.label}
                </label>

                {field.customRender ? (
                  field.customRender(field, formData, handleInputChange)
                ) : field.type === 'select' ? (
                  <select
                    id={field.name}
                    value={formData[field.name] || ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    className="input w-full"
                  >
                    <option value="">-- No Change --</option>
                    {field.options?.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'text' ? (
                  <input
                    type="text"
                    id={field.name}
                    value={formData[field.name] || ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    placeholder={field.placeholder || ''}
                    className="input w-full"
                  />
                ) : field.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    id={field.name}
                    checked={formData[field.name] || false}
                    onChange={(e) => handleInputChange(field.name, e.target.checked)}
                    className="w-5 h-5 rounded border-2 border-gray-300 cursor-pointer"
                    style={{ accentColor: 'var(--color-1)' }}
                  />
                ) : null}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end space-x-4 p-6 bg-tertiary border-t border-tertiary">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-6 py-2.5 text-secondary hover:text-primary hover:bg-secondary rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="px-8 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-medium shadow-sm"
            >
              {saving && (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              <span>{saving ? 'Saving...' : 'Update Selected'}</span>
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
