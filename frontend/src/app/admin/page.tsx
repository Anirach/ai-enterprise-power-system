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
  MessageSquare
} from 'lucide-react'

const API_URL = typeof window !== 'undefined' ? 'http://localhost:8000' : 'http://backend:8000'

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

  const fetchData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [servicesRes, modelsRes, systemRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/services`),
        fetch(`${API_URL}/api/admin/models`),
        fetch(`${API_URL}/api/admin/system-info`)
      ])

      if (servicesRes.ok) setServices(await servicesRes.json())
      if (modelsRes.ok) setModels(await modelsRes.json())
      if (systemRes.ok) setSystemInfo(await systemRes.json())
    } catch (error) {
      console.error('Failed to fetch admin data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handlePullModel = async () => {
    if (!pullModelName.trim()) return

    setIsPulling(true)
    try {
      const res = await fetch(`${API_URL}/api/admin/models/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: pullModelName })
      })
      if (res.ok) {
        setPullModelName('')
        setTimeout(fetchData, 2000)
      }
    } catch (error) {
      console.error('Failed to pull model:', error)
    } finally {
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
    { name: 'API Documentation', url: '/docs', icon: MessageSquare, color: 'text-blue-400' },
    { name: 'n8n Automation', url: 'http://localhost:5678', icon: Zap, color: 'text-orange-400' },
    { name: 'Qdrant Dashboard', url: 'http://localhost:6333/dashboard', icon: Database, color: 'text-purple-400' },
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

        {/* Quick Links */}
        <div className="bg-dark-300 rounded-xl border border-gray-800">
          <div className="p-4 border-b border-gray-800">
            <h3 className="font-medium">Quick Links</h3>
          </div>
          <div className="p-4 space-y-3">
            {quickLinks.map((link) => (
              <a
                key={link.name}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-3 bg-dark-400 rounded-lg hover:bg-dark-200 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <link.icon className={`w-5 h-5 ${link.color}`} />
                  <span>{link.name}</span>
                </div>
                <ExternalLink className="w-4 h-4 text-gray-500" />
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* AI Models */}
      <div className="bg-dark-300 rounded-xl border border-gray-800">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <h3 className="font-medium">AI Models (Ollama)</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={pullModelName}
              onChange={(e) => setPullModelName(e.target.value)}
              placeholder="llama3.2:3b"
              className="bg-dark-400 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary-500"
            />
            <button
              onClick={handlePullModel}
              disabled={!pullModelName.trim() || isPulling}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 rounded-lg text-sm transition-colors"
            >
              <Download className="w-4 h-4" />
              {isPulling ? 'Pulling...' : 'Pull Model'}
            </button>
          </div>
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
                  className="p-4 bg-dark-400 rounded-lg border border-gray-700"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{model.name}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        Size: {formatBytes(model.size)}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {new Date(model.modified_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteModel(model.name)}
                      className="p-2 text-gray-500 hover:text-red-400 transition-colors"
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


