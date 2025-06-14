'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/lib/auth'
import { simulationService, SimulationRequest, SimulationRun } from '@/lib/simulation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  ShieldCheckIcon,
  PlayIcon,
  ArrowLeftIcon,
  DocumentTextIcon,
  CpuChipIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

export default function SimulatePage() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isRunning, setIsRunning] = useState(false)
  const [currentRun, setCurrentRun] = useState<SimulationRun | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')

  // Form state
  const [formData, setFormData] = useState<SimulationRequest>({
    asset_value_min: 50000,
    asset_value_mode: 150000,
    asset_value_max: 500000,
    occurrence_counts: [0, 1, 2, 3, 4, 5],
    occurrence_probabilities: [0.3, 0.4, 0.2, 0.06, 0.03, 0.01],
    iterations: 10000,
    flaw_a_mu: 9.2,
    flaw_a_sigma: 1.0,
    flaw_b_scale: 5000,
    flaw_b_alpha: 2.5,
    threshold_point1: 100000,
    threshold_point2: 50000,
    range_point3: 20000,
    range_point4: 100000,
    scenario_name: '',
    description: ''
  })

  const templates = simulationService.getScenarioTemplates()

  useEffect(() => {
    const checkAuth = async () => {
      if (!authService.isAuthenticated()) {
        router.push('/')
        return
      }
      setIsAuthenticated(true)
      setIsLoading(false)
    }

    checkAuth()
  }, [router])

  const handleTemplateSelect = (templateName: string) => {
    const template = templates.find(t => t.name === templateName)
    if (template) {
      setSelectedTemplate(templateName)
      setFormData({
        ...formData,
        ...template.template,
        scenario_name: template.name,
        description: template.description
      })
      toast.success(`Loaded ${template.name} template`)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.scenario_name.trim()) {
      toast.error('Please enter a scenario name')
      return
    }

    if (formData.occurrence_probabilities.reduce((a, b) => a + b, 0) !== 1) {
      toast.error('Occurrence probabilities must sum to 1.0')
      return
    }

    setIsRunning(true)
    
    try {
      const response = await simulationService.startSimulation(formData)
      toast.success('Simulation started successfully!')
      
      // Poll for results
      const result = await simulationService.waitForSimulationCompletion(response.run_id)
      setCurrentRun(result)
      
      if (result.status === 'completed') {
        toast.success('Simulation completed!')
      } else {
        toast.error(`Simulation failed: ${result.error_message}`)
      }
    } catch (error) {
      console.error('Simulation failed:', error)
      toast.error('Simulation failed. Please try again.')
    } finally {
      setIsRunning(false)
    }
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleArrayInputChange = (field: string, index: number, value: number) => {
    setFormData(prev => ({
      ...prev,
      [field]: (prev[field as keyof SimulationRequest] as number[]).map((item, i) => 
        i === index ? value : item
      )
    }))
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <CpuChipIcon className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="mr-4">
                <ArrowLeftIcon className="w-5 h-5 text-gray-600 hover:text-gray-900" />
              </Link>
              <PlayIcon className="w-6 h-6 text-green-500 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">New Risk Simulation</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Simulation Form */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Simulation Configuration</h2>
                <p className="text-sm text-gray-600">Configure your Monte Carlo risk analysis parameters</p>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Templates */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Quick Start Templates
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {templates.map((template) => (
                      <button
                        key={template.name}
                        type="button"
                        onClick={() => handleTemplateSelect(template.name)}
                        className={`p-4 text-left border rounded-lg transition-colors ${
                          selectedTemplate === template.name
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <h3 className="font-medium text-gray-900">{template.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Basic Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Scenario Name *
                    </label>
                    <input
                      type="text"
                      value={formData.scenario_name}
                      onChange={(e) => handleInputChange('scenario_name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., E-commerce Data Breach"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Iterations
                    </label>
                    <select
                      value={formData.iterations}
                      onChange={(e) => handleInputChange('iterations', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value={1000}>1,000 (Fast)</option>
                      <option value={10000}>10,000 (Standard)</option>
                      <option value={50000}>50,000 (High Precision)</option>
                      <option value={100000}>100,000 (Maximum)</option>
                    </select>
                  </div>
                </div>

                {/* Asset Values */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Asset Values (£)</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Minimum</label>
                      <input
                        type="number"
                        value={formData.asset_value_min}
                        onChange={(e) => handleInputChange('asset_value_min', parseFloat(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Most Likely</label>
                      <input
                        type="number"
                        value={formData.asset_value_mode}
                        onChange={(e) => handleInputChange('asset_value_mode', parseFloat(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Maximum</label>
                      <input
                        type="number"
                        value={formData.asset_value_max}
                        onChange={(e) => handleInputChange('asset_value_max', parseFloat(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Occurrence Rates */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Annual Occurrence Rates</h3>
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
                    {formData.occurrence_counts.map((count, index) => (
                      <div key={index}>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          {count} events
                        </label>
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.01"
                          value={formData.occurrence_probabilities[index]}
                          onChange={(e) => handleArrayInputChange('occurrence_probabilities', index, parseFloat(e.target.value))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Sum: {formData.occurrence_probabilities.reduce((a, b) => a + b, 0).toFixed(3)} (must equal 1.000)
                  </p>
                </div>

                {/* Submit Button */}
                <div className="pt-6 border-t border-gray-200">
                  <button
                    type="submit"
                    disabled={isRunning}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
                  >
                    {isRunning ? (
                      <>
                        <CpuChipIcon className="w-5 h-5 mr-2 animate-spin" />
                        Running Simulation...
                      </>
                    ) : (
                      <>
                        <PlayIcon className="w-5 h-5 mr-2" />
                        Start Simulation
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Progress/Status */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Simulation Status</h3>
              
              {isRunning && (
                <div className="text-center">
                  <CpuChipIcon className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
                  <p className="text-gray-600">Running Monte Carlo simulation...</p>
                  <p className="text-sm text-gray-500 mt-2">
                    {formData.iterations.toLocaleString()} iterations
                  </p>
                </div>
              )}
              
              {currentRun && !isRunning && (
                <div className="space-y-4">
                  <div className="flex items-center">
                    {currentRun.status === 'completed' ? (
                      <CheckCircleIcon className="w-6 h-6 text-green-500 mr-2" />
                    ) : currentRun.status === 'failed' ? (
                      <ExclamationCircleIcon className="w-6 h-6 text-red-500 mr-2" />
                    ) : (
                      <ClockIcon className="w-6 h-6 text-yellow-500 mr-2" />
                    )}
                    <span className="font-medium capitalize">{currentRun.status}</span>
                  </div>
                  
                  {currentRun.results && (
                    <div className="space-y-3">
                      <div>
                        <h4 className="font-medium text-gray-900">Annualized Loss Expectancy</h4>
                        <p className="text-2xl font-bold text-blue-600">
                          £{currentRun.results.ale.toLocaleString()}
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-gray-600">Risk Level</p>
                          <span className={`font-medium ${
                            currentRun.results.risk_assessment.level === 'Low' ? 'text-green-600' :
                            currentRun.results.risk_assessment.level === 'Medium' ? 'text-yellow-600' :
                            currentRun.results.risk_assessment.level === 'High' ? 'text-orange-600' :
                            'text-red-600'
                          }`}>
                            {currentRun.results.risk_assessment.level}
                          </span>
                        </div>
                        <div>
                          <p className="text-gray-600">Loss Probability</p>
                          <p className="font-medium">{(currentRun.results.prob2 * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                      
                      <div className="pt-4 border-t border-gray-200">
                        <Link
                          href={`/results/${currentRun.run_id}`}
                          className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
                        >
                          <DocumentTextIcon className="w-4 h-4 mr-2" />
                          View Detailed Results
                        </Link>
                      </div>
                    </div>
                  )}
                  
                  {currentRun.error_message && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <p className="text-sm text-red-800">{currentRun.error_message}</p>
                    </div>
                  )}
                </div>
              )}
              
              {!isRunning && !currentRun && (
                <div className="text-center text-gray-500">
                  <p>Configure your scenario and click "Start Simulation" to begin</p>
                </div>
              )}
            </div>

            {/* Help */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-blue-900 mb-3">Need Help?</h3>
              <div className="space-y-2 text-sm text-blue-800">
                <p>• Use templates for quick setup</p>
                <p>• Higher iterations = more precision</p>
                <p>• Occurrence probabilities must sum to 1.0</p>
                <p>• Asset values represent financial impact</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
} 