'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authService } from '@/lib/auth'
import { simulationService, OptimizationRequest, OptimizationResult } from '@/lib/simulation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Cog6ToothIcon,
  ArrowLeftIcon,
  CpuChipIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CurrencyPoundIcon,
  ShieldCheckIcon,
  WrenchScrewdriverIcon
} from '@heroicons/react/24/outline'

export default function OptimizePage() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')

  // Form state
  const [formData, setFormData] = useState<OptimizationRequest>({
    historical_data: [
      [2, 3, 1, 4, 2, 3, 1, 2, 3],
      [1, 2, 3, 2, 1, 2, 3, 1, 2],
      [3, 2, 4, 1, 3, 2, 4, 3, 2],
      [1, 1, 2, 2, 1, 1, 2, 1, 1]
    ],
    safeguard_effects: [85, 78, 92, 70, 88, 82, 95, 87, 80],
    maintenance_loads: [45, 52, 38, 65, 42, 48, 35, 44, 50],
    current_controls: [2, 1, 3, 1],
    control_costs: [10000, 15000, 8000, 5000],
    control_limits: [5, 4, 6, 3],
    safeguard_target: 90.0,
    maintenance_limit: 50.0,
    optimization_name: '',
    control_names: ['Firewalls', 'IDS/IPS', 'Endpoint Protection', 'Security Training']
  })

  const templates = simulationService.getOptimizationTemplates()

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
        optimization_name: template.name
      })
      toast.success(`Loaded ${template.name} template`)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.optimization_name.trim()) {
      toast.error('Please enter an optimization name')
      return
    }

    if (formData.safeguard_target <= 0 || formData.maintenance_limit <= 0) {
      toast.error('Please set valid targets and limits')
      return
    }

    setIsOptimizing(true)
    
    try {
      const result = await simulationService.optimizeControls(formData)
      setOptimizationResult(result)
      toast.success('Optimization completed!')
    } catch (error) {
      console.error('Optimization failed:', error)
      toast.error('Optimization failed. Please try again.')
    } finally {
      setIsOptimizing(false)
    }
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleControlCostChange = (index: number, value: number) => {
    setFormData(prev => ({
      ...prev,
      control_costs: prev.control_costs.map((cost, i) => i === index ? value : cost)
    }))
  }

  const handleCurrentControlChange = (index: number, value: number) => {
    setFormData(prev => ({
      ...prev,
      current_controls: prev.current_controls.map((count, i) => i === index ? value : count)
    }))
  }

  const handleControlLimitChange = (index: number, value: number) => {
    setFormData(prev => ({
      ...prev,
      control_limits: prev.control_limits.map((limit, i) => i === index ? value : limit)
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
              <Cog6ToothIcon className="w-6 h-6 text-blue-500 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">Control Optimization</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Optimization Form */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Optimization Configuration</h2>
                <p className="text-sm text-gray-600">Find the most cost-effective security control deployment</p>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Templates */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Quick Start Templates
                  </label>
                  <div className="grid grid-cols-1 gap-3">
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Optimization Name *
                  </label>
                  <input
                    type="text"
                    value={formData.optimization_name}
                    onChange={(e) => handleInputChange('optimization_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Q4 Security Stack Optimization"
                    required
                  />
                </div>

                {/* Control Configuration */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Security Controls</h3>
                  <div className="space-y-4">
                    {formData.control_names?.map((name, index) => (
                      <div key={index} className="grid grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Control Type</label>
                          <div className="font-medium text-gray-900">{name}</div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Current Count</label>
                          <input
                            type="number"
                            min="0"
                            value={formData.current_controls[index]}
                            onChange={(e) => handleCurrentControlChange(index, parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Unit Cost (£)</label>
                          <input
                            type="number"
                            min="0"
                            value={formData.control_costs[index]}
                            onChange={(e) => handleControlCostChange(index, parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Max Limit</label>
                          <input
                            type="number"
                            min="0"
                            value={formData.control_limits[index]}
                            onChange={(e) => handleControlLimitChange(index, parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Optimization Targets */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Optimization Targets</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Minimum Safeguard Effect
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        value={formData.safeguard_target}
                        onChange={(e) => handleInputChange('safeguard_target', parseFloat(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">Target effectiveness score (0-100)</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Maximum Maintenance Load
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        value={formData.maintenance_limit}
                        onChange={(e) => handleInputChange('maintenance_limit', parseFloat(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">Maximum maintenance burden (0-100)</p>
                    </div>
                  </div>
                </div>

                {/* Submit Button */}
                <div className="pt-6 border-t border-gray-200">
                  <button
                    type="submit"
                    disabled={isOptimizing}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
                  >
                    {isOptimizing ? (
                      <>
                        <CpuChipIcon className="w-5 h-5 mr-2 animate-spin" />
                        Optimizing...
                      </>
                    ) : (
                      <>
                        <Cog6ToothIcon className="w-5 h-5 mr-2" />
                        Optimize Controls
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Optimization Status */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Optimization Status</h3>
              
              {isOptimizing && (
                <div className="text-center">
                  <CpuChipIcon className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
                  <p className="text-gray-600">Running linear programming optimization...</p>
                </div>
              )}
              
              {optimizationResult && !isOptimizing && (
                <div className="space-y-4">
                  <div className="flex items-center">
                    <CheckCircleIcon className="w-6 h-6 text-green-500 mr-2" />
                    <span className="font-medium capitalize">{optimizationResult.status}</span>
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Total Additional Cost</h4>
                      <p className="text-2xl font-bold text-blue-600">
                        £{optimizationResult.results.total_additional_cost.toLocaleString()}
                      </p>
                    </div>
                    
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-900">Recommendations</h4>
                      {optimizationResult.results.recommendations.length > 0 ? (
                        <div className="space-y-2">
                          {optimizationResult.results.recommendations.map((rec, index) => (
                            <div key={index} className="bg-gray-50 p-3 rounded-lg">
                              <div className="flex justify-between items-start">
                                <div>
                                  <h5 className="font-medium text-gray-900">{rec.control_type}</h5>
                                  <p className="text-sm text-gray-600">
                                    Add {rec.recommended_additional} units
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className="font-medium text-gray-900">
                                    £{rec.total_cost.toLocaleString()}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <div className="flex items-center">
                            <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />
                            <p className="text-sm text-green-800">
                              Current deployment is already optimal!
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {!isOptimizing && !optimizationResult && (
                <div className="text-center text-gray-500">
                  <p>Configure your controls and click "Optimize Controls" to begin</p>
                </div>
              )}
            </div>

            {/* Current Investment Summary */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Current Investment</h3>
              
              <div className="space-y-3">
                {formData.control_names?.map((name, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">{name}</p>
                      <p className="text-sm text-gray-600">
                        {formData.current_controls[index]} units
                      </p>
                    </div>
                    <p className="font-medium text-gray-900">
                      £{(formData.current_controls[index] * formData.control_costs[index]).toLocaleString()}
                    </p>
                  </div>
                ))}
                
                <div className="pt-3 border-t border-gray-200">
                  <div className="flex justify-between items-center">
                    <p className="font-medium text-gray-900">Total Current Cost</p>
                    <p className="text-lg font-bold text-gray-900">
                      £{formData.current_controls.reduce((total, count, index) => 
                        total + (count * formData.control_costs[index]), 0
                      ).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Help */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-blue-900 mb-3">How It Works</h3>
              <div className="space-y-2 text-sm text-blue-800">
                <p>• Linear programming finds optimal control mix</p>
                <p>• Minimizes cost while meeting security targets</p>
                <p>• Considers current deployment and constraints</p>
                <p>• Provides actionable recommendations</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
} 