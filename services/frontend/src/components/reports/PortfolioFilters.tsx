import { useTheme } from '../../contexts/ThemeContext'

interface PortfolioFiltersProps {
  filters: {
    dateRange: string
    team: string
    project: string
    witType: string
    status: string
    priority: string
  }
  onFiltersChange: (filters: any) => void
}

export default function PortfolioFilters({ filters, onFiltersChange }: PortfolioFiltersProps) {
  const { theme } = useTheme()

  const handleFilterChange = (key: string, value: string) => {
    onFiltersChange({
      ...filters,
      [key]: value
    })
  }

  return (
    <div className="bg-secondary border border-default rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-primary">Filters</h3>
        <button
          onClick={() => onFiltersChange({
            dateRange: '90',
            team: '',
            project: '',
            witType: '',
            status: '',
            priority: ''
          })}
          className="text-xs text-secondary hover:text-primary transition-colors"
        >
          Reset Filters
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
        {/* Date Range */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Date Range</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.dateRange}
            onChange={(e) => handleFilterChange('dateRange', e.target.value)}
          >
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="180">Last 180 days</option>
            <option value="365">Last 1 year</option>
            <option value="all">All time</option>
          </select>
        </div>

        {/* Team */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Team</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.team}
            onChange={(e) => handleFilterChange('team', e.target.value)}
          >
            <option value="">All Teams</option>
            <option value="team1">Team Alpha (SOON)</option>
            <option value="team2">Team Beta (SOON)</option>
          </select>
        </div>

        {/* Project */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Project</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.project}
            onChange={(e) => handleFilterChange('project', e.target.value)}
          >
            <option value="">All Projects</option>
            <option value="proj1">Project A (SOON)</option>
            <option value="proj2">Project B (SOON)</option>
          </select>
        </div>

        {/* Work Item Type */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Work Item Type</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.witType}
            onChange={(e) => handleFilterChange('witType', e.target.value)}
          >
            <option value="">All Types</option>
            <option value="epic">Epic (SOON)</option>
            <option value="story">Story (SOON)</option>
            <option value="task">Task (SOON)</option>
          </select>
        </div>

        {/* Status */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Status</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="todo">To Do (SOON)</option>
            <option value="inprogress">In Progress (SOON)</option>
            <option value="done">Done (SOON)</option>
          </select>
        </div>

        {/* Priority */}
        <div className="flex flex-col">
          <label className="text-xs text-secondary mb-1">Priority</label>
          <select
            className="bg-primary border border-default rounded px-2 py-2 text-sm"
            value={filters.priority}
            onChange={(e) => handleFilterChange('priority', e.target.value)}
          >
            <option value="">All Priorities</option>
            <option value="high">High (SOON)</option>
            <option value="medium">Medium (SOON)</option>
            <option value="low">Low (SOON)</option>
          </select>
        </div>
      </div>
    </div>
  )
}

