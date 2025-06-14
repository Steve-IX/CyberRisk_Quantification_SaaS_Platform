'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/lib/auth'
import { simulationService, SimulationRun } from '@/lib/simulation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { 
  ShieldCheckIcon, 
  ChartBarIcon, 
  CpuChipIcon, 
  DocumentChartBarIcon,
  PlayIcon,
  Cog6ToothIcon,
  UserIcon,
  ArrowRightIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'

export default function Dashboard() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [recentSimulations, setRecentSimulations] = useState<SimulationRun[]>([])
  const [apiHealth, setApiHealth] = useState<any>(null)

  useEffect(() => {
    const checkAuth = async () => {
      if (!authService.isAuthenticated()) {
        // Auto-login with demo token for development
        try {
          await authService.createDemoToken()
          setIsAuthenticated(true)
          toast.success('Welcome to CyberRisk Platform!')
        } catch (error) {
          toast.error('Authentication failed')
          setIsAuthenticated(false)
        }
      } else {
        setIsAuthenticated(true)
      }
      setIsLoading(false)
    }

    checkAuth()
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      loadRecentData()
    }
  }, [isAuthenticated])

  const loadRecentData = async () => {
    try {
      // Load recent simulations
      const simulations = await simulationService.listSimulations(5, 0)
      setRecentSimulations(simulations.simulations)

      // Check API health
      const health = await authService.healthCheck()
      setApiHealth(health)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      toast.error('Failed to load dashboard data')
    }
  }

  const handleLogout = () => {
    authService.logout()
    setIsAuthenticated(false)
    toast.success('Logged out successfully')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <CpuChipIcon className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading CyberRisk Platform...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-lg">
          <div className="text-center">
            <ShieldCheckIcon className="w-16 h-16 text-blue-500 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-gray-900">CyberRisk</h2>
            <p className="text-gray-600">Quantitative Risk Analysis Platform</p>
          </div>
          
          <button
            onClick={async () => {
              try {
                await authService.createDemoToken()
                setIsAuthenticated(true)
                toast.success('Welcome to CyberRisk Platform!')
              } catch (error) {
                toast.error('Authentication failed')
              }
            }}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
          >
            Enter Demo Mode
          </button>
          
          <p className="text-xs text-gray-500 text-center">
            Demo mode provides full access to all features with sample data
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <ShieldCheckIcon className="w-8 h-8 text-blue-500 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">CyberRisk Platform</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-gray-600">
                <div className={`w-2 h-2 rounded-full mr-2 ${apiHealth?.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`} />
                API {apiHealth?.status || 'checking...'}
              </div>
              
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
              >
                <UserIcon className="w-5 h-5" />
                <span>Demo User</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Welcome to CyberRisk Quantification
          </h2>
          <p className="text-gray-600">
            Transform your security risks into actionable business intelligence with Monte Carlo simulation and control optimization.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Link href="/simulate" className="group">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <PlayIcon className="w-8 h-8 text-green-500 mb-2" />
                  <h3 className="font-medium text-gray-900">New Simulation</h3>
                  <p className="text-sm text-gray-600">Run Monte Carlo risk analysis</p>
                </div>
                <ArrowRightIcon className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </div>
          </Link>

          <Link href="/optimize" className="group">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Cog6ToothIcon className="w-8 h-8 text-blue-500 mb-2" />
                  <h3 className="font-medium text-gray-900">Optimize Controls</h3>
                  <p className="text-sm text-gray-600">Find optimal security investments</p>
                </div>
                <ArrowRightIcon className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </div>
          </Link>

          <Link href="/history" className="group">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <ChartBarIcon className="w-8 h-8 text-purple-500 mb-2" />
                  <h3 className="font-medium text-gray-900">View History</h3>
                  <p className="text-sm text-gray-600">Review past simulations</p>
                </div>
                <ArrowRightIcon className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </div>
          </Link>

          <Link href="/reports" className="group">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <DocumentChartBarIcon className="w-8 h-8 text-orange-500 mb-2" />
                  <h3 className="font-medium text-gray-900">Generate Reports</h3>
                  <p className="text-sm text-gray-600">NIS2 & CSRD compliance</p>
                </div>
                <ArrowRightIcon className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
              </div>
            </div>
          </Link>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Simulations */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Recent Simulations</h3>
              <p className="text-sm text-gray-600">Your latest risk analysis runs</p>
            </div>
            
            <div className="p-6">
              {recentSimulations.length > 0 ? (
                <div className="space-y-4">
                  {recentSimulations.map((sim) => (
                    <div key={sim.run_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <h4 className="font-medium text-gray-900">{sim.scenario_name || 'Unnamed Scenario'}</h4>
                        <p className="text-sm text-gray-600">
                          {new Date(sim.created_at).toLocaleDateString()} • {sim.iterations.toLocaleString()} iterations
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          sim.status === 'completed' ? 'bg-green-100 text-green-800' :
                          sim.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {sim.status}
                        </span>
                        {sim.results?.ale && (
                          <span className="text-sm font-medium text-gray-900">
                            £{sim.results.ale.toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <ChartBarIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No simulations yet</p>
                  <Link href="/simulate" className="text-blue-600 hover:text-blue-500 font-medium">
                    Run your first simulation
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Getting Started */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Getting Started</h3>
              <p className="text-sm text-gray-600">Quick guide to risk quantification</p>
            </div>
            
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">1</div>
                  <div>
                    <h4 className="font-medium text-gray-900">Define Your Scenario</h4>
                    <p className="text-sm text-gray-600">Choose from templates or create custom risk scenarios</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">2</div>
                  <div>
                    <h4 className="font-medium text-gray-900">Run Monte Carlo Simulation</h4>
                    <p className="text-sm text-gray-600">Generate quantitative risk metrics with statistical precision</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">3</div>
                  <div>
                    <h4 className="font-medium text-gray-900">Optimize Controls</h4>
                    <p className="text-sm text-gray-600">Find the most cost-effective security investments</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">4</div>
                  <div>
                    <h4 className="font-medium text-gray-900">Generate Reports</h4>
                    <p className="text-sm text-gray-600">Export compliance-ready documentation</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-6 pt-6 border-t border-gray-200">
                <Link 
                  href="/simulate" 
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
                >
                  <PlayIcon className="w-4 h-4 mr-2" />
                  Start Your First Simulation
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Platform Status Banner */}
        {apiHealth?.status !== 'healthy' && (
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400 mr-3" />
              <div>
                <h4 className="font-medium text-yellow-800">API Connection Issue</h4>
                <p className="text-sm text-yellow-700">
                  Some features may be unavailable. Please ensure the FastAPI backend is running on port 8000.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
