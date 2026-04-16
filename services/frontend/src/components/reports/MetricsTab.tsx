import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Activity, CheckCircle } from 'lucide-react'

interface MetricsTabProps {
  filters: any
}

export default function MetricsTab({ filters }: MetricsTabProps) {
  // Placeholder metrics data
  const metrics = [
    {
      id: 1,
      title: 'Total Items',
      value: '156',
      change: '+12%',
      trend: 'up',
      icon: Activity
    },
    {
      id: 2,
      title: 'Completed Items',
      value: '89',
      change: '+8%',
      trend: 'up',
      icon: CheckCircle
    },
    {
      id: 3,
      title: 'In Progress',
      value: '45',
      change: '-3%',
      trend: 'down',
      icon: TrendingUp
    },
    {
      id: 4,
      title: 'Blocked Items',
      value: '12',
      change: '+2',
      trend: 'down',
      icon: TrendingDown
    }
  ]

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, index) => {
          const Icon = metric.icon
          return (
            <motion.div
              key={metric.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="bg-secondary border border-default rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-secondary">{metric.title}</span>
                <Icon className="w-5 h-5 text-secondary" />
              </div>
              <div className="flex items-end justify-between">
                <span className="text-2xl font-bold text-primary">{metric.value}</span>
                <span
                  className={`text-sm font-medium ${
                    metric.trend === 'up' ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {metric.change}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Detailed Metrics Section */}
      <div className="bg-secondary border border-default rounded-lg p-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Detailed Metrics</h3>
        <p className="text-sm text-secondary mb-4">
          Portfolio metrics for the selected period ({filters.dateRange} days)
        </p>

        <div className="space-y-4">
          {/* Velocity Chart Placeholder */}
          <div className="bg-primary border border-default rounded-lg p-4">
            <h4 className="text-sm font-medium text-primary mb-2">Velocity Trend</h4>
            <div className="h-48 flex items-center justify-center text-secondary">
              📊 Chart placeholder - Velocity over time
            </div>
          </div>

          {/* Cycle Time Chart Placeholder */}
          <div className="bg-primary border border-default rounded-lg p-4">
            <h4 className="text-sm font-medium text-primary mb-2">Cycle Time Distribution</h4>
            <div className="h-48 flex items-center justify-center text-secondary">
              📈 Chart placeholder - Cycle time distribution
            </div>
          </div>
        </div>
      </div>

      {/* Placeholder for future enhancements */}
      <div className="bg-secondary border border-default rounded-lg p-4">
        <p className="text-sm text-secondary text-center py-8">
          🚧 Advanced metrics and analytics coming soon
        </p>
      </div>
    </div>
  )
}

