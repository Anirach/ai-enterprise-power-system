'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  Upload, 
  FileText, 
  Globe, 
  Trash2, 
  RefreshCw, 
  CheckCircle,
  XCircle,
  Clock,
  Search,
  FolderOpen
} from 'lucide-react'

const API_URL = typeof window !== 'undefined' ? 'http://localhost:8000' : 'http://backend:8000'

interface Document {
  id: string
  filename: string
  file_type: string
  status: string
  chunks_count: number
  created_at: string
  metadata: Record<string, any>
}

interface Stats {
  total_documents: number
  by_status: {
    completed: number
    processing: number
    failed: number
  }
  total_chunks: number
  vector_store: {
    collection: string
    vectors_count: number
  }
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isCrawling, setIsCrawling] = useState(false)
  const [crawlUrl, setCrawlUrl] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge/documents`)
      if (res.ok) {
        const data = await res.json()
        setDocuments(data)
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error)
    }
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
    fetchStats()
    const interval = setInterval(() => {
      fetchDocuments()
      fetchStats()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchDocuments, fetchStats])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_URL}/api/knowledge/upload`, {
        method: 'POST',
        body: formData
      })
      if (res.ok) {
        fetchDocuments()
        fetchStats()
      }
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setIsUploading(false)
      e.target.value = ''
    }
  }

  const handleCrawl = async () => {
    if (!crawlUrl.trim()) return

    setIsCrawling(true)
    try {
      const res = await fetch(`${API_URL}/api/knowledge/crawl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: crawlUrl, follow_links: false })
      })
      if (res.ok) {
        setCrawlUrl('')
        fetchDocuments()
      }
    } catch (error) {
      console.error('Crawl failed:', error)
    } finally {
      setIsCrawling(false)
    }
  }

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    try {
      const res = await fetch(`${API_URL}/api/knowledge/documents/${docId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        fetchDocuments()
        fetchStats()
      }
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'processing':
      case 'crawling':
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return null
    }
  }

  const getFileIcon = (fileType: string) => {
    if (fileType === 'web') return <Globe className="w-5 h-5 text-blue-400" />
    return <FileText className="w-5 h-5 text-gray-400" />
  }

  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge Base</h1>
          <p className="text-gray-500">Manage your documents and web sources</p>
        </div>
        <button
          onClick={() => { fetchDocuments(); fetchStats(); }}
          className="p-2 text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
            <p className="text-2xl font-bold text-primary-400">{stats.total_documents}</p>
            <p className="text-sm text-gray-500">Total Documents</p>
          </div>
          <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
            <p className="text-2xl font-bold text-green-400">{stats.by_status.completed}</p>
            <p className="text-sm text-gray-500">Processed</p>
          </div>
          <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
            <p className="text-2xl font-bold text-yellow-400">{stats.by_status.processing}</p>
            <p className="text-sm text-gray-500">Processing</p>
          </div>
          <div className="bg-dark-300 rounded-xl p-4 border border-gray-800">
            <p className="text-2xl font-bold text-purple-400">{stats.total_chunks}</p>
            <p className="text-sm text-gray-500">Total Chunks</p>
          </div>
        </div>
      )}

      {/* Upload & Crawl */}
      <div className="grid grid-cols-2 gap-4">
        {/* File Upload */}
        <div className="bg-dark-300 rounded-xl p-6 border border-gray-800">
          <h3 className="font-medium mb-4 flex items-center gap-2">
            <Upload className="w-5 h-5 text-primary-400" />
            Upload Document
          </h3>
          <label className="flex flex-col items-center justify-center h-32 border-2 border-dashed border-gray-700 rounded-xl cursor-pointer hover:border-primary-500 transition-colors">
            <input
              type="file"
              onChange={handleUpload}
              accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.txt,.md,.csv,.html,.htm,.png,.jpg,.jpeg,.tiff"
              className="hidden"
              disabled={isUploading}
            />
            {isUploading ? (
              <div className="flex items-center gap-2 text-gray-400">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Processing with Docling...</span>
              </div>
            ) : (
              <>
                <FolderOpen className="w-8 h-8 text-gray-500 mb-2" />
                <p className="text-sm text-gray-400">Click to upload or drag and drop</p>
                <p className="text-xs text-gray-600 mt-1">PDF, DOCX, PPTX, XLSX, HTML, Images (OCR)</p>
              </>
            )}
          </label>
        </div>

        {/* Web Crawl */}
        <div className="bg-dark-300 rounded-xl p-6 border border-gray-800">
          <h3 className="font-medium mb-4 flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-400" />
            Crawl Website
          </h3>
          <div className="flex gap-2">
            <input
              type="url"
              value={crawlUrl}
              onChange={(e) => setCrawlUrl(e.target.value)}
              placeholder="https://example.com"
              className="flex-1 bg-dark-400 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary-500"
            />
            <button
              onClick={handleCrawl}
              disabled={!crawlUrl.trim() || isCrawling}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
            >
              {isCrawling ? 'Crawling...' : 'Crawl'}
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            Extract content from a webpage and add to knowledge base
          </p>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-dark-300 rounded-xl border border-gray-800">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <h3 className="font-medium">Documents</h3>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="bg-dark-400 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-primary-500"
            />
          </div>
        </div>

        {filteredDocuments.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            <FolderOpen className="w-12 h-12 mx-auto mb-4 text-gray-600" />
            <p>No documents yet</p>
            <p className="text-sm">Upload files or crawl websites to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                className="p-4 flex items-center justify-between hover:bg-dark-400 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {getFileIcon(doc.file_type)}
                  <div>
                    <p className="font-medium">{doc.filename}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                      <span className="flex items-center gap-1">
                        {getStatusIcon(doc.status)}
                        {doc.status}
                      </span>
                      <span>{doc.chunks_count} chunks</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 text-gray-500 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}


