import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { TreePine, BarChart3, LayoutDashboard, List } from 'lucide-react'
import Header from '../../components/Header'
import CollapsedSidebar from '../../components/CollapsedSidebar'
import useDocumentTitle from '../../hooks/useDocumentTitle'
import { useTheme } from '../../contexts/ThemeContext'
import PortfolioFilters from '../../components/reports/PortfolioFilters'
import TreeViewTab from '../../components/reports/TreeViewTab'
import MetricsTab from '../../components/reports/MetricsTab'
import DashboardTab from '../../components/reports/DashboardTab'
import ItemsTab from '../../components/reports/ItemsTab'

type TabType = 'tree-view' | 'metrics' | 'dashboard' | 'items'

interface Tab {
  id: TabType
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const tabs: Tab[] = [
  { id: 'tree-view', label: 'Tree View', icon: TreePine },
  { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'items', label: 'Items', icon: List }
]

export default function PortfolioReportPage() {
  useDocumentTitle('Portfolio Report')
  const { theme } = useTheme()
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Get active tab from URL or default to 'tree-view'
  const activeTabFromUrl = (searchParams.get('tab') as TabType) || 'tree-view'
  const [activeTab, setActiveTab] = useState<TabType>(activeTabFromUrl)

  // Filters state - shared across all tabs
  const [filters, setFilters] = useState({
    dateRange: '90',
    team: '',
    project: '',
    witType: '',
    status: '',
    priority: ''
  })

  // Handle tab change and update URL
  const handleTabChange = (tabId: TabType) => {
    setActiveTab(tabId)
    setSearchParams({ tab: tabId })
  }

  // Handle filter changes
  const handleFiltersChange = (newFilters: typeof filters) => {
    setFilters(newFilters)
  }

  // Render active tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'tree-view':
        return <TreeViewTab filters={filters} />
      case 'metrics':
        return <MetricsTab filters={filters} />
      case 'dashboard':
        return <DashboardTab filters={filters} />
      case 'items':
        return <ItemsTab filters={filters} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-primary">
      <Header />
      <div className="flex">
        <CollapsedSidebar />
        <main className="flex-1 ml-16 py-8">
          <div className="ml-12 mr-12">
            {/* Page Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-6"
            >
              <h1 className="text-3xl font-bold text-primary mb-2">Portfolio Report</h1>
              <p className="text-secondary">Comprehensive portfolio analysis and insights</p>
            </motion.div>

            {/* Filters Section - Applies to all tabs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="mb-6"
            >
              <PortfolioFilters filters={filters} onFiltersChange={handleFiltersChange} />
            </motion.div>

            {/* Tabs Navigation */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mb-6"
            >
              <div className="border-b border-default">
                <div className="flex space-x-1">
                  {tabs.map((tab) => {
                    const Icon = tab.icon
                    const isActive = activeTab === tab.id
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
                        className={`flex items-center space-x-2 px-4 py-3 border-b-2 transition-all duration-200 ${
                          isActive
                            ? 'border-[color:var(--color-1)] text-primary font-medium'
                            : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{tab.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </motion.div>

            {/* Tab Content */}
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {renderTabContent()}
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  )
}

