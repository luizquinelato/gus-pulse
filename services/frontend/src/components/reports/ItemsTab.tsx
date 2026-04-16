import { motion } from 'framer-motion'
import { Search, Filter, Download, ExternalLink } from 'lucide-react'
import { useState } from 'react'

interface ItemsTabProps {
  filters: any
}

export default function ItemsTab({ filters }: ItemsTabProps) {
  const [searchQuery, setSearchQuery] = useState('')

  // Placeholder items data
  const items = [
    {
      id: 'EPIC-001',
      title: 'Platform Modernization',
      type: 'Epic',
      status: 'In Progress',
      priority: 'High',
      assignee: 'John Doe',
      progress: 65
    },
    {
      id: 'STORY-042',
      title: 'Migrate to React 18',
      type: 'Story',
      status: 'In Progress',
      priority: 'Medium',
      assignee: 'Jane Smith',
      progress: 80
    },
    {
      id: 'STORY-043',
      title: 'Update API Gateway',
      type: 'Story',
      status: 'To Do',
      priority: 'High',
      assignee: 'Bob Johnson',
      progress: 0
    },
    {
      id: 'EPIC-002',
      title: 'Customer Portal',
      type: 'Epic',
      status: 'In Progress',
      priority: 'Medium',
      assignee: 'Alice Williams',
      progress: 45
    },
    {
      id: 'STORY-044',
      title: 'User Dashboard',
      type: 'Story',
      status: 'Done',
      priority: 'High',
      assignee: 'Charlie Brown',
      progress: 100
    }
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Done':
        return 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
      case 'In Progress':
        return 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
      case 'To Do':
        return 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400'
      default:
        return 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'High':
        return 'text-red-600 dark:text-red-400'
      case 'Medium':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'Low':
        return 'text-green-600 dark:text-green-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  return (
    <div className="space-y-4">
      {/* Search and Actions Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-secondary" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-primary border border-default rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[color:var(--color-1)]"
          />
        </div>
        <button className="flex items-center space-x-2 px-4 py-2 bg-secondary border border-default rounded-lg text-sm hover:bg-tertiary transition-colors">
          <Filter className="w-4 h-4" />
          <span>More Filters</span>
        </button>
        <button className="flex items-center space-x-2 px-4 py-2 bg-secondary border border-default rounded-lg text-sm hover:bg-tertiary transition-colors">
          <Download className="w-4 h-4" />
          <span>Export</span>
        </button>
      </div>

      {/* Items Table */}
      <div className="bg-secondary border border-default rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-tertiary border-b border-default">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Title</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Priority</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Assignee</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Progress</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-secondary uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-default">
              {items.map((item, index) => (
                <motion.tr
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  className="hover:bg-tertiary transition-colors"
                >
                  <td className="px-4 py-3 text-sm font-medium text-primary">{item.id}</td>
                  <td className="px-4 py-3 text-sm text-primary">{item.title}</td>
                  <td className="px-4 py-3 text-sm text-secondary">{item.type}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-sm font-medium ${getPriorityColor(item.priority)}`}>{item.priority}</td>
                  <td className="px-4 py-3 text-sm text-secondary">{item.assignee}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-[color:var(--color-1)] h-2 rounded-full transition-all duration-300"
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-secondary w-10 text-right">{item.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button className="text-secondary hover:text-primary transition-colors">
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Placeholder */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-secondary">Showing 5 of 156 items</p>
        <div className="flex items-center space-x-2">
          <button className="px-3 py-1 bg-secondary border border-default rounded text-sm hover:bg-tertiary transition-colors">
            Previous
          </button>
          <button className="px-3 py-1 bg-secondary border border-default rounded text-sm hover:bg-tertiary transition-colors">
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

