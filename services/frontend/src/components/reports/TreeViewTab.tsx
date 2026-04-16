import { motion } from 'framer-motion'
import { Plus, Minus, Circle, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'

interface TreeViewTabProps {
  filters: any
}

interface WorkItemTreeNode {
  id: number
  external_id?: string
  key?: string
  summary?: string
  wit_name?: string
  wit_to?: string
  level_name?: string
  level_number?: number
  status_name?: string
  priority?: string
  assignee?: string
  story_points?: number
  parent_external_id?: string
  children: WorkItemTreeNode[]
}

export default function TreeViewTab({ filters }: TreeViewTabProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set())
  const [treeData, setTreeData] = useState<WorkItemTreeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const toggleNode = (nodeId: number) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId)
    } else {
      newExpanded.add(nodeId)
    }
    setExpandedNodes(newExpanded)
  }

  useEffect(() => {
    const fetchTreeData = async () => {
      setLoading(true)
      setError(null)

      try {
        const token = localStorage.getItem('pulse_token')
        if (!token) {
          throw new Error('No authentication token found')
        }

        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'

        // Build query parameters from filters
        const params = new URLSearchParams()
        if (filters.team) params.append('team', filters.team)
        if (filters.project) params.append('project_id', filters.project)
        if (filters.witType) params.append('wit_type', filters.witType)
        if (filters.status) params.append('status', filters.status)
        if (filters.priority) params.append('priority', filters.priority)

        const url = `${apiBase}/api/v1/portfolio/tree${params.toString() ? `?${params.toString()}` : ''}`

        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error(`Failed to fetch tree data: ${response.statusText}`)
        }

        const data = await response.json()
        console.log('Portfolio tree data received:', data)
        console.log('Total items:', data.total_items)
        console.log('Root items:', data.tree?.length)
        setTreeData(data.tree || [])
      } catch (err) {
        console.error('Error fetching tree data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load tree data')
      } finally {
        setLoading(false)
      }
    }

    fetchTreeData()
  }, [filters])

  const renderTreeNode = (node: WorkItemTreeNode, level: number = 0) => {
    const isExpanded = expandedNodes.has(node.id)
    const hasChildren = node.children && node.children.length > 0

    // Build display name
    const displayName = node.key
      ? `${node.key}: ${node.summary || 'No summary'}`
      : node.summary || 'Untitled'

    return (
      <div key={node.id}>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className={`flex items-center space-x-2 py-2 px-3 hover:bg-tertiary rounded ${hasChildren ? 'cursor-pointer' : ''}`}
          style={{ paddingLeft: `${level * 24 + 12}px` }}
          onClick={() => hasChildren && toggleNode(node.id)}
        >
          {/* Expand/Collapse Icon */}
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
            {hasChildren ? (
              isExpanded ? (
                <Minus className="w-4 h-4 text-blue-500" />
              ) : (
                <Plus className="w-4 h-4 text-blue-500" />
              )
            ) : (
              <Circle className="w-2 h-2 text-gray-400 fill-current" />
            )}
          </div>

          <div className="flex-1 flex items-center space-x-2 flex-wrap">
            <span className="text-sm text-primary font-medium">{displayName}</span>
            {node.level_name && (
              <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded font-semibold">
                {node.level_name}
              </span>
            )}
            {node.status_name && (
              <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
                {node.status_name}
              </span>
            )}
            {node.priority && (
              <span className="text-xs text-secondary">
                P: {node.priority}
              </span>
            )}
            {node.story_points && (
              <span className="text-xs text-secondary">
                SP: {node.story_points}
              </span>
            )}
            {node.assignee && (
              <span className="text-xs text-secondary ml-auto">
                👤 {node.assignee}
              </span>
            )}
            {hasChildren && (
              <span className="text-xs text-gray-400">
                ({node.children.length} {node.children.length === 1 ? 'child' : 'children'})
              </span>
            )}
          </div>
        </motion.div>

        {hasChildren && isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            {node.children.map((child) => renderTreeNode(child, level + 1))}
          </motion.div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-secondary border border-default rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-primary">Portfolio Hierarchy</h3>
            <p className="text-sm text-secondary mt-1">
              Hierarchical view of work items based on parent-child relationships
            </p>
          </div>
          {!loading && !error && (
            <div className="text-sm text-secondary">
              {treeData.length} root item{treeData.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-secondary animate-spin" />
            <span className="ml-2 text-sm text-secondary">Loading portfolio tree...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-sm text-red-600 dark:text-red-400">
              ⚠️ {error}
            </p>
          </div>
        )}

        {!loading && !error && treeData.length === 0 && (
          <div className="bg-tertiary border border-default rounded-lg p-8 text-center">
            <p className="text-sm text-secondary">
              No work items found matching the current filters.
            </p>
          </div>
        )}

        {!loading && !error && treeData.length > 0 && (
          <div className="bg-primary border border-default rounded-lg p-2 max-h-[600px] overflow-y-auto">
            {treeData.map((node) => renderTreeNode(node))}
          </div>
        )}
      </div>

      {/* Stats section */}
      {!loading && !error && treeData.length > 0 && (
        <div className="bg-secondary border border-default rounded-lg p-4">
          <h4 className="text-sm font-semibold text-primary mb-2">Quick Actions</h4>
          <div className="flex space-x-2">
            <button
              onClick={() => {
                // Expand all nodes
                const allIds = new Set<number>()
                const collectIds = (nodes: WorkItemTreeNode[]) => {
                  nodes.forEach(node => {
                    if (node.children && node.children.length > 0) {
                      allIds.add(node.id)
                      collectIds(node.children)
                    }
                  })
                }
                collectIds(treeData)
                setExpandedNodes(allIds)
              }}
              className="px-3 py-1.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              Expand All
            </button>
            <button
              onClick={() => setExpandedNodes(new Set())}
              className="px-3 py-1.5 text-xs bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
            >
              Collapse All
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

