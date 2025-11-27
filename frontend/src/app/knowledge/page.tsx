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
  FolderOpen,
  Eye,
  Download,
  X,
  Tag,
  FileType,
  Calendar,
  Hash,
  Languages
} from 'lucide-react'

const API_URL = typeof window !== 'undefined' ? 'http://localhost:8000' : 'http://backend:8000'

interface Document {
  id: string
  name: string
  file_type: string
  content_type?: string
  file_size: number
  status: string
  chunks_count: number
  page_count: number
  word_count: number
  language: string
  tags: string[]
  created_at: string
  metadata: Record<string, any>
  progress: number
}

interface DocumentContent {
  id: string
  name: string
  content: string | null
  chunks_count: number
}

interface Stats {
  total_documents: number
  by_status: {
    completed: number
    processing: number
    failed: number
  }
  total_chunks: number
  total_size: number
  vector_store: {
    collection: string
    vectors_count: number
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Progress Bar Component
function ProgressBar({ status, progress = 0 }: { status: string; progress?: number }) {
  const getProgressColor = () => {
    if (status === 'completed') return 'bg-green-500'
    if (status === 'failed') return 'bg-red-500'
    if (status === 'processing' || status === 'crawling') return 'bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500'
    return 'bg-gray-600'
  }

  const displayProgress = status === 'completed' ? 100 : status === 'failed' ? 100 : progress

  return (
    <div className="mt-2">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-500">
          {status === 'processing' && progress < 40 && 'Parsing document...'}
          {status === 'processing' && progress >= 40 && progress < 80 && 'Generating embeddings...'}
          {status === 'processing' && progress >= 80 && 'Storing in database...'}
          {status === 'completed' && 'Complete'}
          {status === 'failed' && 'Failed'}
        </span>
        <span className="text-xs font-medium text-gray-400">{displayProgress}%</span>
      </div>
      <div className="w-full h-2 bg-dark-400 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ease-out ${getProgressColor()}`}
          style={{ width: `${displayProgress}%` }}
        />
      </div>
    </div>
  )
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isCrawling, setIsCrawling] = useState(false)
  const [crawlUrl, setCrawlUrl] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [docContent, setDocContent] = useState<DocumentContent | null>(null)
  const [isLoadingContent, setIsLoadingContent] = useState(false)
  const [showViewer, setShowViewer] = useState(false)
  const [isClearing, setIsClearing] = useState(false)

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
      } else {
        const error = await res.json()
        alert(`Upload failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please check if the backend is running.')
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

  const handleDelete = async (docId: string, docName: string) => {
    if (!confirm(`Are you sure you want to delete "${docName}"?\n\nThis will remove the document from:\n- MinIO (file storage)\n- PostgreSQL (metadata)\n- Qdrant (vector embeddings)`)) return

    try {
      const res = await fetch(`${API_URL}/api/knowledge/documents/${docId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        fetchDocuments()
        fetchStats()
        if (selectedDoc?.id === docId) {
          setSelectedDoc(null)
          setShowViewer(false)
        }
      } else {
        const error = await res.json()
        alert(`Delete failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const handleClearAll = async () => {
    if (!confirm(`⚠️ WARNING: Clear ALL Knowledge Base?\n\nThis will permanently delete:\n- All ${documents.length} documents\n- All files from MinIO\n- All vector embeddings from Qdrant\n- All metadata from PostgreSQL\n\nThis action cannot be undone!`)) return

    setIsClearing(true)
    try {
      const res = await fetch(`${API_URL}/api/knowledge/clear-all`, {
        method: 'DELETE'
      })
      if (res.ok) {
        const result = await res.json()
        alert(`Cleared ${result.deleted_count} documents successfully!`)
        fetchDocuments()
        fetchStats()
        setSelectedDoc(null)
        setShowViewer(false)
      } else {
        const error = await res.json()
        alert(`Clear failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Clear all failed:', error)
      alert('Clear all failed. Please check if the backend is running.')
    } finally {
      setIsClearing(false)
    }
  }

  const handleViewDocument = async (doc: Document) => {
    setSelectedDoc(doc)
    setShowViewer(true)
    setIsLoadingContent(true)
    setDocContent(null)

    try {
      const res = await fetch(`${API_URL}/api/knowledge/documents/${doc.id}/content`)
      if (res.ok) {
        const data = await res.json()
        setDocContent(data)
      }
    } catch (error) {
      console.error('Failed to fetch content:', error)
    } finally {
      setIsLoadingContent(false)
    }
  }

  const handleDownload = async (doc: Document) => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge/documents/${doc.id}/download`)
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = doc.name
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
      console.error('Download failed:', error)
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
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge Base</h1>
          <p className="text-gray-500">Manage your documents and web sources</p>
        </div>
        <div className="flex items-center gap-2">
          {documents.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={isClearing}
              className="px-3 py-2 bg-red-600/20 text-red-400 hover:bg-red-600/30 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              {isClearing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              Clear All
            </button>
          )}
          <button
            onClick={() => { fetchDocuments(); fetchStats(); }}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
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
                className="p-4 hover:bg-dark-400 transition-colors cursor-pointer"
                onClick={() => handleViewDocument(doc)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    {getFileIcon(doc.file_type)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{doc.name}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-500 mt-1 flex-wrap">
                        <span className="flex items-center gap-1">
                          {getStatusIcon(doc.status)}
                          {doc.status}
                        </span>
                        {doc.file_size > 0 && (
                          <span>{formatBytes(doc.file_size)}</span>
                        )}
                        {doc.page_count > 0 && (
                          <span>{doc.page_count} pages</span>
                        )}
                        {doc.word_count > 0 && (
                          <span>{doc.word_count.toLocaleString()} words</span>
                        )}
                        <span>{doc.chunks_count} chunks</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleViewDocument(doc); }}
                      className="p-2 text-gray-500 hover:text-primary-400 transition-colors"
                      title="View content"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {doc.file_type !== 'web' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownload(doc); }}
                        className="p-2 text-gray-500 hover:text-blue-400 transition-colors"
                        title="Download original"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.name); }}
                      className="p-2 text-gray-500 hover:text-red-400 transition-colors"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {/* Progress Bar */}
                <div className="ml-9 mr-2">
                  <ProgressBar status={doc.status} progress={doc.progress} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Viewer Modal */}
      {showViewer && selectedDoc && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6">
          <div className="bg-dark-300 rounded-2xl border border-gray-800 w-full max-w-4xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getFileIcon(selectedDoc.file_type)}
                <div>
                  <h3 className="font-medium">{selectedDoc.name}</h3>
                  <p className="text-xs text-gray-500">
                    {getStatusIcon(selectedDoc.status)} {selectedDoc.status}
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setShowViewer(false); setSelectedDoc(null); setDocContent(null); }}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Metadata */}
            <div className="p-4 border-b border-gray-800 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <FileType className="w-4 h-4 text-gray-500" />
                <span className="text-gray-400">Type:</span>
                <span>{selectedDoc.file_type}</span>
              </div>
              {selectedDoc.file_size > 0 && (
                <div className="flex items-center gap-2">
                  <Hash className="w-4 h-4 text-gray-500" />
                  <span className="text-gray-400">Size:</span>
                  <span>{formatBytes(selectedDoc.file_size)}</span>
                </div>
              )}
              {selectedDoc.page_count > 0 && (
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-500" />
                  <span className="text-gray-400">Pages:</span>
                  <span>{selectedDoc.page_count}</span>
                </div>
              )}
              {selectedDoc.word_count > 0 && (
                <div className="flex items-center gap-2">
                  <Hash className="w-4 h-4 text-gray-500" />
                  <span className="text-gray-400">Words:</span>
                  <span>{selectedDoc.word_count.toLocaleString()}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Languages className="w-4 h-4 text-gray-500" />
                <span className="text-gray-400">Language:</span>
                <span>{selectedDoc.language}</span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span className="text-gray-400">Created:</span>
                <span>{new Date(selectedDoc.created_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <Hash className="w-4 h-4 text-gray-500" />
                <span className="text-gray-400">Chunks:</span>
                <span>{selectedDoc.chunks_count}</span>
              </div>
              {selectedDoc.tags && selectedDoc.tags.length > 0 && (
                <div className="flex items-center gap-2 col-span-2">
                  <Tag className="w-4 h-4 text-gray-500" />
                  <span className="text-gray-400">Tags:</span>
                  <div className="flex gap-1 flex-wrap">
                    {selectedDoc.tags.map((tag, i) => (
                      <span key={i} className="px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded text-xs">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {isLoadingContent ? (
                <div className="flex items-center justify-center h-full">
                  <RefreshCw className="w-8 h-8 text-gray-500 animate-spin" />
                </div>
              ) : docContent?.content ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-gray-300 text-sm font-sans leading-relaxed">
                    {docContent.content}
                  </pre>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <FileText className="w-12 h-12 mb-4" />
                  <p>No content available</p>
                  <p className="text-sm">Document may still be processing</p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-800 flex justify-between">
              <button
                onClick={() => handleDelete(selectedDoc.id, selectedDoc.name)}
                className="px-4 py-2 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete Document
              </button>
              <div className="flex gap-2">
                {selectedDoc.file_type !== 'web' && (
                  <button
                    onClick={() => handleDownload(selectedDoc)}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download Original
                  </button>
                )}
                <button
                  onClick={() => { setShowViewer(false); setSelectedDoc(null); setDocContent(null); }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
