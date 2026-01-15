'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Server,
  Cpu,
  HardDrive,
  Activity,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Download,
  Trash2,
  ExternalLink,
  Zap,
  Database,
  MessageSquare,
  FileBox,
  Bot,
  Workflow,
  BookOpen
} from 'lucide-react'

const API_URL = typeof window !== 'undefined' ? 'http://localhost:3602' : 'http://backend:8000'

// Popular models from Ollama library (https://ollama.com/search?c=tools)
const POPULAR_MODELS = [
  // OpenAI Open-Weight Models
  { name: 'gpt-oss:20b', size: '12GB', desc: 'OpenAI - Reasoning & Tools', category: 'featured' },
  { name: 'gpt-oss:120b', size: '70GB', desc: 'OpenAI - Most Powerful', category: 'featured' },
  // Meta Llama
  { name: 'llama3.2:3b', size: '2GB', desc: 'Meta - Fast & capable', category: 'general' },
  { name: 'llama3.2:1b', size: '1.3GB', desc: 'Meta - Lightweight', category: 'general' },
  { name: 'llama3.1:8b', size: '4.7GB', desc: 'Meta - More powerful', category: 'general' },
  { name: 'llama3.3:70b', size: '40GB', desc: 'Meta - State of the art', category: 'large' },
  // Alibaba Qwen
  { name: 'qwen2.5:3b', size: '1.9GB', desc: 'Alibaba - Multilingual', category: 'general' },
  { name: 'qwen2.5:7b', size: '4.4GB', desc: 'Alibaba - Strong reasoning', category: 'general' },
  { name: 'qwen3:8b', size: '4.9GB', desc: 'Alibaba - Latest gen', category: 'general' },
  // DeepSeek
  { name: 'deepseek-r1:8b', size: '4.9GB', desc: 'DeepSeek - Reasoning', category: 'reasoning' },
  { name: 'deepseek-r1:14b', size: '9GB', desc: 'DeepSeek - Better reasoning', category: 'reasoning' },
  // Microsoft
  { name: 'phi4-mini:3.8b', size: '2.5GB', desc: 'Microsoft - Efficient', category: 'general' },
  // Mistral
  { name: 'mistral:7b', size: '4.1GB', desc: 'Mistral AI - Popular', category: 'general' },
  { name: 'mistral-small:22b', size: '13GB', desc: 'Mistral - Small model', category: 'general' },
  // Google
  { name: 'gemma2:2b', size: '1.6GB', desc: 'Google - Compact', category: 'general' },
  { name: 'gemma2:9b', size: '5.4GB', desc: 'Google - Capable', category: 'general' },
  // IBM
  { name: 'granite3.3:8b', size: '4.9GB', desc: 'IBM - Enterprise', category: 'general' },
  // Coding
  { name: 'qwen2.5-coder:7b', size: '4.4GB', desc: 'Alibaba - Code specialist', category: 'coding' },
  { name: 'devstral:24b', size: '14GB', desc: 'Mistral - Code agent', category: 'coding' },
]

interface ServiceStatus {
  name: string
  status: string
  details: Record<string, any>
}

interface Model {
  name: string
  size: number
  modified_at: string
  digest: string
  is_active: boolean
}

interface SystemInfo {
  platform: string
  python_version: string
  cpu_count?: number
  cpu_percent?: number
  memory?: {
    total_gb: number
    used_gb: number
    percent: number
  }
  disk?: {
    total_gb: number
    used_gb: number
    percent: number
  }
}

export default function AdminPage() {
  const [services, setServices] = useState<ServiceStatus[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [pullModelName, setPullModelName] = useState('')
  const [isPulling, setIsPulling] = useState(false)
  const [pullStatus, setPullStatus] = useState<string | null>(null)
  const [pullProgress, setPullProgress] = useState<number>(0)
  const [showModelDropdown, setShowModelDropdown] = useState(false)

  const reconnectToPullStream = useCallback((model: string) => {
    const eventSource = new EventSource(`${API_URL}/api/admin/models/pull/${encodeURIComponent(model)}/stream`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.status === 'success') {
          setPullStatus(`✅ Successfully pulled ${model}`)
          setPullProgress(100)
          setPullModelName('')
          eventSource.close()
          setIsPulling(false)
        } else if (data.status === 'error') {
          setPullStatus(`❌ Error: ${data.message}`)
          eventSource.close()
          setIsPulling(false)
        } else {
          setPullProgress(data.progress || 0)
          setPullStatus(`⏳ ${data.details || data.status || 'Downloading...'}`)
        }
      } catch (e) {
        console.error('Parse error:', e)
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
    }
    
    return eventSource
  }, [])
  
  const fetchData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [servicesRes, modelsRes, systemRes, pullStatusRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/services`),
        fetch(`${API_URL}/api/admin/models`),
        fetch(`${API_URL}/api/admin/system-info`),
        fetch(`${API_URL}/api/admin/models/pull/status`)
      ])

      if (servicesRes.ok) setServices(await servicesRes.json())
      if (modelsRes.ok) setModels(await modelsRes.json())
      if (systemRes.ok) setSystemInfo(await systemRes.json())
      
      // Check if there's an ongoing pull (only if not already pulling)
      if (pullStatusRes.ok && !isPulling) {
        const pullData = await pullStatusRes.json()
        if (pullData.pulling && pullData.model) {
          setIsPulling(true)
          setPullModelName(pullData.model)
          setPullProgress(pullData.progress || 0)
          setPullStatus(`⏳ ${pullData.details || pullData.status || 'Downloading...'}`)
          reconnectToPullStream(pullData.model)
        }
      }
    } catch (error) {
      console.error('Failed to fetch admin data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [isPulling, reconnectToPullStream])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handlePullModel = async (modelToPull?: string) => {
    const model = modelToPull || pullModelName.trim()
    if (!model) return

    setIsPulling(true)
    setPullModelName(model)
    setPullProgress(0)
    setPullStatus(`⏳ Starting download of ${model}...`)
    setShowModelDropdown(false)
    
    try {
      // Use EventSource for Server-Sent Events
      const eventSource = new EventSource(`${API_URL}/api/admin/models/pull/${encodeURIComponent(model)}/stream`)
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.status === 'success') {
            setPullStatus(`✅ Successfully pulled ${model}`)
            setPullProgress(100)
            setPullModelName('')
            eventSource.close()
            setTimeout(() => {
              fetchData()
              setPullStatus(null)
              setPullProgress(0)
            }, 3000)
            setIsPulling(false)
          } else if (data.status === 'error') {
            setPullStatus(`❌ Error: ${data.message}`)
            eventSource.close()
            setTimeout(() => {
              setPullStatus(null)
              setPullProgress(0)
            }, 5000)
            setIsPulling(false)
          } else {
            // Update progress
            setPullProgress(data.progress || 0)
            
            // Format status message
            let statusMsg = data.status || 'Downloading...'
            if (data.total > 0) {
              const completedMB = (data.completed / 1024 / 1024).toFixed(1)
              const totalMB = (data.total / 1024 / 1024).toFixed(1)
              statusMsg = `${data.status}: ${completedMB} MB / ${totalMB} MB`
            }
            setPullStatus(`⏳ ${statusMsg}`)
          }
        } catch (e) {
          console.error('Parse error:', e)
        }
      }
      
      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        eventSource.close()
        // Check if model was actually pulled despite error
        setTimeout(async () => {
          try {
            const res = await fetch(`${API_URL}/api/admin/models`)
            const models = await res.json()
            if (models.some((m: Model) => m.name === model)) {
              setPullStatus(`✅ Successfully pulled ${model}`)
              setPullProgress(100)
              fetchData()
            } else {
              setPullStatus(`❌ Connection error. Please try again.`)
            }
          } catch {
            setPullStatus(`❌ Connection error. Please try again.`)
          }
          setTimeout(() => {
            setPullStatus(null)
            setPullProgress(0)
          }, 3000)
          setIsPulling(false)
        }, 1000)
      }
      
    } catch (error) {
      console.error('Failed to pull model:', error)
      setPullStatus(`❌ Error: ${error instanceof Error ? error.message : 'Network error'}`)
      setTimeout(() => {
        setPullStatus(null)
        setPullProgress(0)
      }, 5000)
      setIsPulling(false)
    }
  }

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Delete model ${modelName}?`)) return

    try {
      const res = await fetch(`${API_URL}/api/admin/models/${encodeURIComponent(modelName)}`, {
        method: 'DELETE'
      })
      if (res.ok) fetchData()
    } catch (error) {
      console.error('Failed to delete model:', error)
    }
  }

  const handleActivateModel = async (modelName: string) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/models/active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
      })
      if (res.ok) {
        fetchData()
      } else {
        const data = await res.json()
        alert(`Failed to activate model: ${data.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to activate model:', error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'unhealthy':
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'unreachable':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const quickLinks = [
    { name: 'API Documentation', url: 'http://localhost:3602/docs', icon: BookOpen, color: 'text-blue-400', desc: 'FastAPI Swagger UI' },
    { name: 'MinIO Console', url: 'http://localhost:9001', icon: FileBox, color: 'text-red-400', desc: 'Object Storage Management' },
    { name: 'Qdrant Dashboard', url: 'http://localhost:6333/dashboard', icon: Database, color: 'text-purple-400', desc: 'Vector Database UI' },
    { name: 'n8n Automation', url: 'http://localhost:5678', icon: Workflow, color: 'text-orange-400', desc: 'Workflow Automation' },
    { name: 'pgAdmin', url: 'http://localhost:5050', icon: Database, color: 'text-green-400', desc: 'PostgreSQL Admin Panel' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
          <p className="text-gray-500">Monitor and manage system components</p>
        </div>
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-dark-300 border border-gray-700 rounded-lg hover:border-primary-500 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* System Info */}
      {systemInfo && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3 mb-2">
              <Server className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-400">Platform</span>
            </div>
            <p className="text-lg font-medium">{systemInfo.platform}</p>
          </div>

          {systemInfo.cpu_percent !== undefined && (
            <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
              <div className="flex items-center gap-3 mb-2">
                <Cpu className="w-5 h-5 text-blue-400" />
                <span className="text-sm text-gray-400">CPU Usage</span>
              </div>
              <p className="text-lg font-medium">{systemInfo.cpu_percent}%</p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${systemInfo.cpu_percent}%` }}
                />
              </div>
            </div>
          )}

          {systemInfo.memory && (
            <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
              <div className="flex items-center gap-3 mb-2">
                <Activity className="w-5 h-5 text-green-400" />
                <span className="text-sm text-gray-400">Memory</span>
              </div>
              <p className="text-lg font-medium">
                {systemInfo.memory.used_gb} / {systemInfo.memory.total_gb} GB
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${systemInfo.memory.percent}%` }}
                />
              </div>
            </div>
          )}

          {systemInfo.disk && (
            <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
              <div className="flex items-center gap-3 mb-2">
                <HardDrive className="w-5 h-5 text-purple-400" />
                <span className="text-sm text-gray-400">Disk</span>
              </div>
              <p className="text-lg font-medium">
                {systemInfo.disk.used_gb} / {systemInfo.disk.total_gb} GB
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${systemInfo.disk.percent}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Services Status */}
        <div className="bg-dark-300 rounded-xl border border-gray-800">
          <div className="p-4 border-b border-gray-800">
            <h3 className="font-medium">Services Status</h3>
          </div>
          <div className="p-4 space-y-3">
            {services.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Loading services...</p>
            ) : (
              services.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between p-3 bg-dark-400 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <p className="font-medium capitalize">{service.name}</p>
                      <p className="text-xs text-gray-500">
                        {Object.entries(service.details || {})
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(', ') || 'No details'}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      service.status === 'healthy'
                        ? 'bg-green-500/20 text-green-400'
                        : service.status === 'unhealthy'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}
                  >
                    {service.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Links - Web Interfaces */}
        <div className="bg-dark-300 rounded-xl border border-gray-800">
          <div className="p-4 border-b border-gray-800">
            <h3 className="font-medium">🌐 Service Web Interfaces</h3>
            <p className="text-xs text-gray-500 mt-1">Quick access to all service dashboards</p>
          </div>
          <div className="p-4 grid gap-3">
            {quickLinks.map((link) => (
              <a
                key={link.name}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-4 bg-dark-400 rounded-lg hover:bg-dark-200 border border-transparent hover:border-gray-700 transition-all group"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-dark-300 group-hover:scale-110 transition-transform ${link.color}`}>
                    <link.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="font-medium text-gray-200">{link.name}</span>
                    <p className="text-xs text-gray-500">{link.desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 font-mono">{link.url.replace('http://', '')}</span>
                  <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-primary-400 transition-colors" />
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* AI Models */}
      <div className="bg-dark-300 rounded-xl border border-gray-800">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">AI Models (Ollama)</h3>
            <div className="flex gap-2 items-center relative">
              <input
                type="text"
                value={pullModelName}
                onChange={(e) => setPullModelName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isPulling && handlePullModel()}
                onClick={() => setShowModelDropdown(!showModelDropdown)}
                placeholder="Select or type model name"
                className="w-72 bg-dark-400 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary-500 cursor-pointer"
              />
              <button
                onClick={() => handlePullModel()}
                disabled={!pullModelName.trim() || isPulling}
                className="flex items-center gap-2 px-4 py-1.5 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-sm transition-colors whitespace-nowrap"
              >
                <Download className={`w-4 h-4 ${isPulling ? 'animate-bounce' : ''}`} />
                {isPulling ? 'Pulling...' : 'Pull'}
              </button>
            </div>
          </div>
          {pullStatus && (
            <div className={`mt-3 p-3 rounded-lg text-sm ${
              pullStatus.startsWith('✅') ? 'bg-green-500/20 text-green-400' :
              pullStatus.startsWith('❌') ? 'bg-red-500/20 text-red-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <span>{pullStatus}</span>
                {isPulling && pullProgress > 0 && (
                  <span className="text-xs font-mono">{pullProgress}%</span>
                )}
              </div>
              {isPulling && (
                <div className="w-full bg-dark-400 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-primary-500 transition-all duration-300 ease-out"
                    style={{ width: `${Math.max(pullProgress, 2)}%` }}
                  />
                </div>
              )}
            </div>
          )}
          
          {/* Model Selection Dropdown */}
          {showModelDropdown && (
            <div className="mt-4 p-4 bg-dark-400 border border-gray-700 rounded-lg">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <h4 className="text-sm font-medium text-gray-300">Available Models to Pull</h4>
                  <p className="text-xs text-gray-500">Click to select or type any model name above</p>
                </div>
                <button 
                  onClick={() => setShowModelDropdown(false)}
                  className="text-gray-500 hover:text-gray-300 p-1"
                >
                  ✕
                </button>
              </div>
              
              {/* Featured Models */}
              <div className="mb-4">
                <p className="text-xs text-yellow-500 font-medium mb-2">⭐ Featured - OpenAI Open-Weight</p>
                <div className="grid grid-cols-2 gap-2">
                  {POPULAR_MODELS.filter(pm => pm.category === 'featured').map((pm) => {
                    const isInstalled = models.some(m => m.name === pm.name || m.name.startsWith(pm.name.split(':')[0]))
                    return (
                      <button
                        key={pm.name}
                        onClick={() => {
                          setPullModelName(pm.name)
                          setShowModelDropdown(false)
                        }}
                        disabled={isInstalled}
                        className={`text-left p-3 rounded-lg border transition-colors ${
                          isInstalled 
                            ? 'bg-green-500/10 border-green-500/30 cursor-not-allowed' 
                            : 'bg-yellow-500/10 border-yellow-500/30 hover:border-yellow-500 hover:bg-yellow-500/20'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <span className="text-yellow-300 font-medium">{pm.name}</span>
                          {isInstalled && <span className="text-green-500 text-xs">Installed ✓</span>}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">{pm.desc}</div>
                        <div className="text-xs text-gray-500 mt-1">Size: {pm.size}</div>
                      </button>
                    )
                  })}
                </div>
              </div>
              
              {/* General Models */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 font-medium mb-2">🚀 General Purpose</p>
                <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                  {POPULAR_MODELS.filter(pm => pm.category === 'general').map((pm) => {
                    const isInstalled = models.some(m => m.name === pm.name || m.name.startsWith(pm.name.split(':')[0]))
                    return (
                      <button
                        key={pm.name}
                        onClick={() => {
                          setPullModelName(pm.name)
                          setShowModelDropdown(false)
                        }}
                        disabled={isInstalled}
                        className={`text-left p-2 rounded-lg border transition-colors ${
                          isInstalled 
                            ? 'bg-green-500/10 border-green-500/30 cursor-not-allowed' 
                            : 'bg-dark-300 border-gray-700 hover:border-primary-500 hover:bg-dark-200'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <span className="text-gray-200 font-medium text-sm">{pm.name}</span>
                          {isInstalled && <span className="text-green-500 text-xs">✓</span>}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">{pm.size}</div>
                      </button>
                    )
                  })}
                </div>
              </div>
              
              {/* Reasoning & Coding Models */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-xs text-purple-400 font-medium mb-2">🧠 Reasoning</p>
                  <div className="space-y-2">
                    {POPULAR_MODELS.filter(pm => pm.category === 'reasoning').map((pm) => {
                      const isInstalled = models.some(m => m.name === pm.name || m.name.startsWith(pm.name.split(':')[0]))
                      return (
                        <button
                          key={pm.name}
                          onClick={() => {
                            setPullModelName(pm.name)
                            setShowModelDropdown(false)
                          }}
                          disabled={isInstalled}
                          className={`w-full text-left p-2 rounded-lg border transition-colors ${
                            isInstalled 
                              ? 'bg-green-500/10 border-green-500/30 cursor-not-allowed' 
                              : 'bg-dark-300 border-gray-700 hover:border-purple-500 hover:bg-purple-500/10'
                          }`}
                        >
                          <span className="text-gray-200 text-sm">{pm.name}</span>
                          <span className="text-xs text-gray-500 ml-2">{pm.size}</span>
                          {isInstalled && <span className="text-green-500 text-xs ml-2">✓</span>}
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-blue-400 font-medium mb-2">💻 Coding</p>
                  <div className="space-y-2">
                    {POPULAR_MODELS.filter(pm => pm.category === 'coding').map((pm) => {
                      const isInstalled = models.some(m => m.name === pm.name || m.name.startsWith(pm.name.split(':')[0]))
                      return (
                        <button
                          key={pm.name}
                          onClick={() => {
                            setPullModelName(pm.name)
                            setShowModelDropdown(false)
                          }}
                          disabled={isInstalled}
                          className={`w-full text-left p-2 rounded-lg border transition-colors ${
                            isInstalled 
                              ? 'bg-green-500/10 border-green-500/30 cursor-not-allowed' 
                              : 'bg-dark-300 border-gray-700 hover:border-blue-500 hover:bg-blue-500/10'
                          }`}
                        >
                          <span className="text-gray-200 text-sm">{pm.name}</span>
                          <span className="text-xs text-gray-500 ml-2">{pm.size}</span>
                          {isInstalled && <span className="text-green-500 text-xs ml-2">✓</span>}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
              
              <div className="pt-3 border-t border-gray-700">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-500">
                    💡 Tip: Type any model name like <code className="bg-dark-300 px-1 rounded">gpt-oss:20b</code> and click Pull
                  </p>
                  <a 
                    href="https://ollama.com/search?c=tools" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-primary-400 hover:text-primary-300"
                  >
                    Browse all models →
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="p-4">
          {models.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Cpu className="w-12 h-12 mx-auto mb-4 text-gray-600" />
              <p>No models installed</p>
              <p className="text-sm">Pull a model to get started</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {models.map((model) => (
                <div
                  key={model.name}
                  className={`p-4 bg-dark-400 rounded-lg border-2 transition-colors ${
                    model.is_active 
                      ? 'border-green-500 bg-green-500/10' 
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{model.name}</p>
                        {model.is_active && (
                          <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Size: {formatBytes(model.size)}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {new Date(model.modified_at).toLocaleDateString()}
                      </p>
                      {!model.is_active && (
                        <button
                          onClick={() => handleActivateModel(model.name)}
                          className="mt-2 px-3 py-1 text-xs bg-primary-600 hover:bg-primary-700 rounded transition-colors"
                        >
                          Use This Model
                        </button>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteModel(model.name)}
                      disabled={model.is_active}
                      className={`p-2 transition-colors ${
                        model.is_active 
                          ? 'text-gray-600 cursor-not-allowed' 
                          : 'text-gray-500 hover:text-red-400'
                      }`}
                      title={model.is_active ? 'Cannot delete active model' : 'Delete model'}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


