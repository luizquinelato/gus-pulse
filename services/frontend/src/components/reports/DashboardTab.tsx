import { motion } from 'framer-motion'
import { PieChart, BarChart3, Activity, Clock } from 'lucide-react'

interface DashboardTabProps {
  filters: any
}

export default function DashboardTab({ filters }: DashboardTabProps) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="bg-secondary border border-default rounded-lg p-4"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
              <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-sm font-semibold text-primary">Portfolio Health</h3>
          </div>
          <div className="text-2xl font-bold text-primary mb-1">85%</div>
          <p className="text-xs text-secondary">On track items</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="bg-secondary border border-default rounded-lg p-4"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <BarChart3 className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-sm font-semibold text-primary">Completion Rate</h3>
          </div>
          <div className="text-2xl font-bold text-primary mb-1">67%</div>
          <p className="text-xs text-secondary">Items completed</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-secondary border border-default rounded-lg p-4"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
              <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-sm font-semibold text-primary">Avg Cycle Time</h3>
          </div>
          <div className="text-2xl font-bold text-primary mb-1">8.5d</div>
          <p className="text-xs text-secondary">Days per item</p>
        </motion.div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="bg-secondary border border-default rounded-lg p-6"
        >
          <div className="flex items-center space-x-2 mb-4">
            <PieChart className="w-5 h-5 text-secondary" />
            <h3 className="text-lg font-semibold text-primary">Status Distribution</h3>
          </div>
          <div className="h-64 flex items-center justify-center text-secondary">
            🥧 Pie chart placeholder - Status breakdown
          </div>
        </motion.div>

        {/* Progress Over Time */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="bg-secondary border border-default rounded-lg p-6"
        >
          <div className="flex items-center space-x-2 mb-4">
            <BarChart3 className="w-5 h-5 text-secondary" />
            <h3 className="text-lg font-semibold text-primary">Progress Over Time</h3>
          </div>
          <div className="h-64 flex items-center justify-center text-secondary">
            📊 Line chart placeholder - Progress trend
          </div>
        </motion.div>
      </div>

      {/* Team Performance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.5 }}
        className="bg-secondary border border-default rounded-lg p-6"
      >
        <h3 className="text-lg font-semibold text-primary mb-4">Team Performance</h3>
        <p className="text-sm text-secondary mb-4">
          Performance metrics for the selected period ({filters.dateRange} days)
        </p>
        <div className="h-48 flex items-center justify-center text-secondary">
          📈 Bar chart placeholder - Team comparison
        </div>
      </motion.div>

      {/* Placeholder for future enhancements */}
      <div className="bg-secondary border border-default rounded-lg p-4">
        <p className="text-sm text-secondary text-center py-8">
          🚧 Interactive dashboards with real-time data coming soon
        </p>
      </div>
    </div>
  )
}

