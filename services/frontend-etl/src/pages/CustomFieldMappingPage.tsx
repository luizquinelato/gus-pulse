import React, { useState, useEffect, useMemo } from 'react';
import { Loader2, FileText, Save, Search } from 'lucide-react';
import Header from '../components/Header';
import CollapsedSidebar from '../components/CollapsedSidebar';
import BackToTop from '../components/BackToTop';
import ToastContainer from '../components/ToastContainer';

import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import { customFieldsApi, integrationsApi } from '../services/etlApiService';
import {
  Integration,
  CustomField
} from '../types';

// Mapping state: maps custom_field_XX to custom_fields.id
interface FieldMappingState {
  [key: string]: number | null; // e.g., { "custom_field_01": 123, "custom_field_02": null, ... }
}

interface CustomFieldMappingPageProps {
  embedded?: boolean
}

// Searchable Select Component
interface SearchableSelectProps {
  value: string | number;
  onChange: (value: string) => void;
  options: CustomField[];
  placeholder: string;
  badgeColor?: string;
}

const SearchableSelect: React.FC<SearchableSelectProps> = ({ value, onChange, options, placeholder, badgeColor = 'var(--color-1)' }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) {
      return options;
    }

    const query = searchQuery.toLowerCase();
    return options.filter(field =>
      field.name.toLowerCase().includes(query) ||
      field.external_id.toLowerCase().includes(query)
    );
  }, [options, searchQuery]);

  // Handle null/undefined/empty string values properly
  const numericValue = value && value !== '' ? Number(value) : null;
  const selectedOption = numericValue ? options.find(f => f.id === numericValue) : null;

  // Reset search when closing
  const handleClose = () => {
    setIsOpen(false);
    setSearchQuery('');
  };

  return (
    <div className="relative">
      {/* Display button showing current selection */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 border border-tertiary/20 rounded-lg bg-primary text-primary text-sm focus:ring-2 focus:ring-accent focus:border-accent transition-all text-left flex items-center justify-between"
      >
        <span className={selectedOption ? '' : 'text-secondary'}>
          {selectedOption ? (
            <div className="flex items-center gap-2 flex-wrap">
              <span>{selectedOption.name} ({selectedOption.external_id})</span>
              {selectedOption.available_in_projects && selectedOption.available_in_projects.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {selectedOption.available_in_projects.map(proj => (
                    <span key={proj.project_key} className="inline-block px-2 py-0.5 text-xs text-white rounded" style={{ backgroundColor: badgeColor }}>
                      {proj.project_key}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : placeholder}
        </span>
        <svg className="w-4 h-4 ml-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={handleClose}
          />

          {/* Dropdown */}
          <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
            <div className="p-2 border-b border-gray-200">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                />
              </div>
            </div>
            <div className="max-h-60 overflow-y-auto">
              <div
                className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                onClick={() => {
                  onChange('');
                  handleClose();
                }}
              >
                {placeholder}
              </div>
              {filteredOptions.map((field) => (
                <div
                  key={field.id}
                  className={`px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm ${
                    field.id === Number(value) ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => {
                    onChange(String(field.id));
                    handleClose();
                  }}
                >
                  <div className="font-medium">
                    {field.name} <span className="text-xs text-gray-500">({field.external_id})</span>
                  </div>
                  {/* NEW: Project badges in dropdown */}
                  {field.available_in_projects && field.available_in_projects.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {field.available_in_projects.map(proj => (
                        <span key={proj.project_key} className="inline-block px-2 py-0.5 text-xs text-white rounded" style={{ backgroundColor: badgeColor }}>
                          {proj.project_key}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {filteredOptions.length === 0 && (
                <div className="px-3 py-2 text-sm text-gray-500 text-center">
                  No fields found
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const CustomFieldMappingPage: React.FC<CustomFieldMappingPageProps> = ({ embedded = false }) => {
  const { user } = useAuth();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedIntegration, setSelectedIntegration] = useState<number | null>(null);
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [fieldMappings, setFieldMappings] = useState<FieldMappingState>({});
  const [originalMappings, setOriginalMappings] = useState<FieldMappingState>({});
  const [selectedMappingKeys, setSelectedMappingKeys] = useState<Set<string>>(new Set());

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [saving, setSaving] = useState(false);
  const { toasts, removeToast, showSuccess, showError } = useToast();

  // Check if there are unsaved changes
  const hasUnsavedChanges = JSON.stringify(fieldMappings) !== JSON.stringify(originalMappings);

  // Load integrations on component mount
  useEffect(() => {
    loadIntegrations();
  }, []);

  // Auto-select first Jira integration when integrations are loaded
  useEffect(() => {
    if (integrations.length > 0 && !selectedIntegration) {
      const jiraIntegration = integrations[0]; // Should be Jira since we filter for it
      setSelectedIntegration(jiraIntegration.id);
      // Load data immediately when auto-selecting
      loadCustomFields(jiraIntegration.id);
      loadMappingConfig(jiraIntegration.id);
    }
  }, [integrations]);

  // Load custom fields and mapping when integration is manually changed
  // Skip if this is the initial auto-selection (already loaded above)
  useEffect(() => {
    if (selectedIntegration && integrations.length > 0) {
      // Only reload if this is NOT the first integration (auto-selected)
      const isFirstIntegration = integrations[0]?.id === selectedIntegration;
      if (!isFirstIntegration) {
        loadCustomFields(selectedIntegration);
        loadMappingConfig(selectedIntegration);
      }
    }
  }, [selectedIntegration]);

  const loadIntegrations = async () => {
    try {
      setLoading(true);
      const response = await integrationsApi.getIntegrations();
      const jiraIntegrations = response.data.filter((integration: Integration) =>
        integration.name?.toLowerCase() === 'jira' && integration.integration_type?.toLowerCase() === 'data'
      );
      setIntegrations(jiraIntegrations);
    } catch (error) {
      console.error('Failed to load integrations:', error);
      showError('Load Failed', 'Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  const loadCustomFields = async (integrationId: number) => {
    try {
      const response = await customFieldsApi.listCustomFields(integrationId, false);
      const data = response.data;

      if (data.success) {
        setCustomFields(data.custom_fields || []);
      }
    } catch (error) {
      console.error('Failed to load custom fields:', error);
      showError('Load Failed', 'Failed to load custom fields from database');
    }
  };

  const loadMappingConfig = async (integrationId: number, skipLoadingState: boolean = false) => {
    try {
      if (!skipLoadingState) {
        setLoadingData(true);
      }
      const response = await customFieldsApi.getMappingsTable(integrationId);
      const data = response.data;

      if (data.success) {
        setFieldMappings(data.mappings || {});
        setOriginalMappings(data.mappings || {}); // Store original for comparison
      }
    } catch (error) {
      console.error('Failed to load mapping config:', error);
      showError('Load Failed', 'Failed to load custom field mappings');
    } finally {
      if (!skipLoadingState) {
        setLoadingData(false);
      }
    }
  };

  const saveMappingConfig = async () => {
    if (!selectedIntegration) return;

    try {
      setSaving(true);

      const response = await customFieldsApi.saveMappingsTable(selectedIntegration, fieldMappings);
      const data = response.data;

      if (data.success) {
        setOriginalMappings(fieldMappings); // Update original after successful save
        showSuccess('Save Successful', 'Custom field mappings saved successfully');
      } else {
        showError('Save Failed', data.message || 'Failed to save custom field mappings');
      }
    } catch (error: any) {
      console.error('Failed to save mapping config:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save custom field mappings';
      showError('Save Failed', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const updateFieldMapping = (fieldKey: string, customFieldId: number | null) => {
    setFieldMappings(prev => ({
      ...prev,
      [fieldKey]: customFieldId
    }));
  };

  // Toggle individual mapping selection
  const handleToggleMappingSelection = (fieldKey: string) => {
    const newSelected = new Set(selectedMappingKeys);
    if (newSelected.has(fieldKey)) {
      newSelected.delete(fieldKey);
    } else {
      newSelected.add(fieldKey);
    }
    setSelectedMappingKeys(newSelected);
  };

  // Toggle all mappings selection (all rows)
  const handleToggleAllMappings = () => {
    const allMappingKeys = [
      ...['acceptance_criteria_field', 'development_field', 'sprints_field', 'story_points_field', 'team_field'],
      ...Array.from({ length: 20 }, (_, i) => `custom_field_${(i + 1).toString().padStart(2, '0')}`)
    ];

    if (selectedMappingKeys.size === allMappingKeys.length) {
      setSelectedMappingKeys(new Set());
    } else {
      setSelectedMappingKeys(new Set(allMappingKeys));
    }
  };

  // Delete selected mappings (set to null in custom_fields_mappings table)
  const handleDeleteSelectedMappings = async () => {
    if (!selectedIntegration) return;

    try {
      // Create updated mappings with selected keys set to null
      const updatedMappings = { ...fieldMappings };
      selectedMappingKeys.forEach(key => {
        updatedMappings[key] = null;
      });

      // Save immediately to database
      const response = await customFieldsApi.saveMappingsTable(selectedIntegration, updatedMappings);
      const data = response.data;

      if (data.success) {
        // Update local state
        setFieldMappings(updatedMappings);
        setOriginalMappings(updatedMappings);
        setSelectedMappingKeys(new Set());

        // Reload from database to confirm
        await loadMappingConfig(selectedIntegration, true);

        // Show success toast
        showSuccess('Delete Successful', 'Selected mappings deleted successfully');
      } else {
        showError('Delete Failed', data.message || 'Failed to delete mappings');
      }
    } catch (error: any) {
      console.error('Failed to delete mappings:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete mappings';
      showError('Delete Failed', errorMessage);
    }
  };

  const content = (
    <div>



            {/* Loading State - Only show while loading integrations */}
            {loading && (
              <div className="bg-secondary rounded-lg shadow-sm p-6">
                <div className="text-center py-12">
                  <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-primary" />
                  <h2 className="text-2xl font-semibold text-primary mb-2">
                    Loading...
                  </h2>
                  <p className="text-secondary">
                    Fetching integrations
                  </p>
                </div>
              </div>
            )}

            {/* No Jira Integration Found */}
            {integrations.length === 0 && !loading && (
              <div className="bg-secondary rounded-lg shadow-sm p-6">
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">🔍</div>
                  <h2 className="text-2xl font-semibold text-primary mb-2">
                    No Jira Integration Found
                  </h2>
                  <p className="text-secondary mb-6">
                    Custom field mapping requires an active Jira integration. Please configure a Jira integration first.
                  </p>
                  <button
                    onClick={() => window.location.href = '/integrations'}
                    className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    Configure Integrations
                  </button>
                </div>
              </div>
            )}

            {/* Custom Field Mappings Table - Show immediately when integrations are loaded */}
            {integrations.length > 0 && !loading && (
              <div className="rounded-lg bg-table-container shadow-md border border-gray-400">
                {/* Sticky Header Section */}
                <div className="sticky top-16 z-20 bg-table-container">
                  <div className="px-6 py-5 flex justify-between items-center bg-table-header rounded-t-lg">
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-semibold text-table-header">Custom Field Mappings</h2>
                      {selectedMappingKeys.size > 0 && (
                        <span className="text-sm text-secondary">
                          ({selectedMappingKeys.size} selected)
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {selectedMappingKeys.size > 0 && (
                        <button
                          onClick={handleDeleteSelectedMappings}
                          className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
                            <path d="M3 6h18"></path>
                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                          </svg>
                          <span className="text-sm font-medium text-primary">Bulk Delete</span>
                        </button>
                      )}
                      <button
                        onClick={saveMappingConfig}
                        disabled={saving || !hasUnsavedChanges}
                        className="px-4 py-2 bg-card border border-border rounded-lg hover:border-accent/40 hover:shadow-sm transition-all flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Save className="h-4 w-4 text-secondary" />
                        <span className="text-sm font-medium text-primary">{saving ? 'Saving...' : 'Save Mappings'}</span>
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto bg-table-column-header">
                    <table className="w-full" style={{ tableLayout: 'fixed' }}>
                      <colgroup>
                        <col style={{ width: '5%' }} />
                        <col style={{ width: '23%' }} />
                        <col style={{ width: '38%' }} />
                        <col style={{ width: '17%' }} />
                        <col style={{ width: '17%' }} />
                      </colgroup>
                      <thead className="bg-table-column-header">
                      <tr className="bg-table-column-header">
                        <th className="px-6 py-4 text-center text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          <input
                            type="checkbox"
                            checked={selectedMappingKeys.size === 25}
                            onChange={handleToggleAllMappings}
                            className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent cursor-pointer"
                          />
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Work Items Column
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Jira Custom Field
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Field Type
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-table-column-header">
                          Jira Field ID
                        </th>
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
                      <col style={{ width: '23%' }} />
                      <col style={{ width: '38%' }} />
                      <col style={{ width: '17%' }} />
                      <col style={{ width: '17%' }} />
                    </colgroup>
                    <tbody>
                        {/* Special Fields Section */}
                        <tr>
                          <td colSpan={5} className="px-6 py-3">
                            <div className="flex items-center">
                              <div className="flex-grow border-t border-gray-300"></div>
                              <span className="px-4 text-xs font-semibold text-white uppercase tracking-wider">
                                Special Fields
                              </span>
                              <div className="flex-grow border-t border-gray-300"></div>
                            </div>
                          </td>
                        </tr>

                        {/* All Special Fields */}
                        {[
                          { key: 'acceptance_criteria_field', label: 'ACCEPTANCE CRITERIA' },
                          { key: 'development_field', label: 'DEVELOPMENT' },
                          { key: 'sprints_field', label: 'SPRINTS' },
                          { key: 'story_points_field', label: 'STORY POINTS' },
                          { key: 'team_field', label: 'TEAM' }
                        ].map((specialField, index) => {
                          const selectedFieldId = fieldMappings[specialField.key];
                          const selectedField = customFields.find(f => f.id === selectedFieldId);

                          return (
                            <tr key={specialField.key} className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'}`}>
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <input
                                  type="checkbox"
                                  checked={selectedMappingKeys.has(specialField.key)}
                                  onChange={() => handleToggleMappingSelection(specialField.key)}
                                  className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent cursor-pointer"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm font-medium text-primary">{specialField.label}</div>
                              </td>
                              <td className="px-6 py-4">
                                <SearchableSelect
                                  value={selectedFieldId || ''}
                                  onChange={(value) => {
                                    setFieldMappings(prev => ({
                                      ...prev,
                                      [specialField.key]: value ? parseInt(value) : null
                                    }));
                                  }}
                                  options={customFields}
                                  placeholder="-- Not Mapped --"
                                  badgeColor="var(--color-1)"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary">
                                {selectedField?.field_type || '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {selectedField ? (
                                  <code className="text-xs text-secondary bg-tertiary/20 px-2 py-1 rounded">
                                    {selectedField.external_id}
                                  </code>
                                ) : (
                                  <span className="text-sm text-secondary">-</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}

                        {/* Custom Fields Section */}
                        <tr>
                          <td colSpan={5} className="px-6 py-3">
                            <div className="flex items-center">
                              <div className="flex-grow border-t border-gray-300"></div>
                              <span className="px-4 text-xs font-semibold text-white uppercase tracking-wider">
                                Custom Fields (20 Available)
                              </span>
                              <div className="flex-grow border-t border-gray-300"></div>
                            </div>
                          </td>
                        </tr>

                        {/* Regular Custom Fields Section */}
                        {Array.from({ length: 20 }, (_, i) => i + 1).map((num, index) => {
                          const fieldKey = `custom_field_${num.toString().padStart(2, '0')}`;
                          const selectedFieldId = fieldMappings[fieldKey];
                          const selectedField = customFields.find(f => f.id === selectedFieldId);

                          return (
                            <tr
                              key={fieldKey}
                              className={`${index % 2 === 0 ? 'bg-table-row-even' : 'bg-table-row-odd'}`}
                            >
                              <td className="px-6 py-5 whitespace-nowrap text-center">
                                <input
                                  type="checkbox"
                                  checked={selectedMappingKeys.has(fieldKey)}
                                  onChange={() => handleToggleMappingSelection(fieldKey)}
                                  className="w-4 h-4 text-accent bg-secondary border-gray-400 rounded focus:ring-accent cursor-pointer"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm font-medium text-primary">Custom Field {num.toString().padStart(2, '0')}</div>
                              </td>
                              <td className="px-6 py-4">
                                <SearchableSelect
                                  value={selectedFieldId || ''}
                                  onChange={(value) => updateFieldMapping(fieldKey, value ? parseInt(value) : null)}
                                  options={customFields}
                                  placeholder="-- Not Mapped --"
                                  badgeColor="var(--color-2)"
                                />
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {selectedField ? (
                                  <span className="text-sm text-secondary">
                                    {selectedField.field_type}
                                  </span>
                                ) : (
                                  <span className="text-sm text-secondary">-</span>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                {selectedField ? (
                                  <code className="text-xs text-secondary bg-tertiary/20 px-2 py-1 rounded">
                                    {selectedField.external_id}
                                  </code>
                                ) : (
                                  <span className="text-sm text-secondary">-</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

      {/* Toast Container - Always show, even in embedded mode */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

      {/* Back to Top Button - Always show, even in embedded mode */}
      <BackToTop />
    </div>
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
  );
};

export default CustomFieldMappingPage;
