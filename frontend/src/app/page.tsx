'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, Sparkles, Loader2, FileText, Globe, ExternalLink, Cpu } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Source {
  text: string
  score: number
  metadata?: {
    filename?: string
    url?: string
    source?: string
    doc_id?: string
    chunk_index?: number
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  model?: string
}

const API_URL = typeof window !== 'undefined' ? 'http://localhost:3602' : 'http://backend:8000'

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [useRag, setUseRag] = useState(true)
  const [activeModel, setActiveModel] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchActiveModel = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/models/active`)
      if (res.ok) {
        const data = await res.json()
        setActiveModel(data.model || '')
      }
    } catch (error) {
      console.error('Failed to fetch active model:', error)
    }
  }, [])

  useEffect(() => {
    fetchActiveModel()
    // Refresh every 30 seconds
    const interval = setInterval(fetchActiveModel, 30000)
    return () => clearInterval(interval)
  }, [fetchActiveModel])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      return 'http://localhost:3602'
    }
    return 'http://backend:8000'
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Create placeholder for streaming response
    const assistantId = (Date.now() + 1).toString()
    const placeholderMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      model: ''
    }
    setMessages(prev => [...prev, placeholderMessage])

    try {
      // Use streaming endpoint for faster perceived response
      const response = await fetch(`${getApiUrl()}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content
          })),
          use_rag: useRag
        })
      })

      if (!response.ok) throw new Error('Failed to get response')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let sources: Source[] = []
      let model = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue
              
              try {
                const parsed = JSON.parse(data)
                
                if (parsed.type === 'sources') {
                  sources = parsed.sources || []
                  model = parsed.model || ''
                } else if (parsed.type === 'chunk') {
                  fullContent += parsed.content
                  // Update message in real-time
                  setMessages(prev => prev.map(m => 
                    m.id === assistantId 
                      ? { ...m, content: fullContent, sources, model }
                      : m
                  ))
                } else if (parsed.type === 'error') {
                  throw new Error(parsed.error)
                }
              } catch (e) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      }

      // Final update with complete content
      setMessages(prev => prev.map(m => 
        m.id === assistantId 
          ? { ...m, content: fullContent, sources, model }
          : m
      ))

    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => prev.map(m => 
        m.id === assistantId
          ? { ...m, content: 'Sorry, I encountered an error. Please make sure the backend is running and Ollama has models loaded.' }
          : m
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">AI Chat</h1>
            <p className="text-sm text-gray-500">Chat with AI using your knowledge base</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Active Model Display */}
            {activeModel && (
              <a 
                href="/admin" 
                className="flex items-center gap-2 px-3 py-1.5 bg-dark-300 border border-gray-700 rounded-lg hover:border-primary-500 transition-colors"
                title="Click to change model"
              >
                <Cpu className="w-4 h-4 text-primary-400" />
                <span className="text-sm text-gray-300">{activeModel}</span>
              </a>
            )}
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-400">Use Knowledge Base</span>
              <Sparkles className={`w-4 h-4 ${useRag ? 'text-primary-400' : 'text-gray-600'}`} />
            </label>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mb-6">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-semibold mb-2">Welcome to AI Power Chat</h2>
            <p className="text-gray-500 max-w-md">
              Ask me anything! I can search through your knowledge base to provide accurate answers.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-3 max-w-lg">
              {[
                'What documents do we have?',
                'Summarize the latest report',
                'How does the system work?',
                'Search for project updates'
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="p-3 text-sm text-left text-gray-400 bg-dark-300 rounded-xl border border-gray-800 hover:border-primary-500/50 hover:text-gray-200 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-4 animate-fade-in ${
              message.role === 'user' ? 'justify-end' : ''
            }`}
          >
            {message.role === 'assistant' && (
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            
            <div className={`max-w-3xl ${message.role === 'user' ? 'order-first' : ''}`}>
              <div
                className={`rounded-2xl px-5 py-4 ${
                  message.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-dark-300 border border-gray-800'
                }`}
              >
{/* Show loading dots when assistant message is empty and loading */}
                {message.role === 'assistant' && !message.content && isLoading ? (
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
                  </div>
                ) : (
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-invert prose-sm max-w-none
                      prose-headings:text-gray-100 prose-headings:font-semibold
                      prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                      prose-p:text-gray-300 prose-p:leading-relaxed
                      prose-a:text-primary-400 prose-a:no-underline hover:prose-a:underline
                      prose-strong:text-gray-100 prose-strong:font-semibold
                      prose-code:text-primary-300 prose-code:bg-dark-400 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
                      prose-pre:bg-dark-400 prose-pre:border prose-pre:border-gray-700 prose-pre:rounded-lg
                      prose-ul:text-gray-300 prose-ol:text-gray-300
                      prose-li:marker:text-primary-400
                      prose-blockquote:border-l-primary-500 prose-blockquote:bg-dark-400/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r
                      prose-table:border-collapse prose-th:bg-dark-400 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-gray-700
                    "
                    components={{
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
                          {children}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                )}
              </div>
              
              {/* Source References - Grouped by Document */}
              {message.sources && message.sources.length > 0 && (() => {
                // Group sources by filename/doc_id
                const groupedSources = message.sources.reduce((acc, source) => {
                  const key = source.metadata?.filename || source.metadata?.doc_id || source.metadata?.url || 'Unknown'
                  if (!acc[key]) {
                    acc[key] = {
                      name: key,
                      isWeb: source.metadata?.source === 'web' || !!source.metadata?.url,
                      url: source.metadata?.url,
                      chunks: []
                    }
                  }
                  acc[key].chunks.push({
                    text: source.text,
                    score: source.score,
                    chunkIndex: source.metadata?.chunk_index
                  })
                  return acc
                }, {} as Record<string, { name: string; isWeb: boolean; url?: string; chunks: { text: string; score: number; chunkIndex?: number }[] }>)
                
                const uniqueSources = Object.values(groupedSources)
                
                return (
                  <div className="mt-4">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="h-px flex-1 bg-gray-800"></div>
                      <span className="text-xs text-gray-500 uppercase tracking-wider px-2">
                        📚 Sources ({uniqueSources.length} document{uniqueSources.length !== 1 ? 's' : ''})
                      </span>
                      <div className="h-px flex-1 bg-gray-800"></div>
                    </div>
                    
                    <div className="grid gap-2">
                      {uniqueSources.map((source, idx) => {
                        const avgScore = source.chunks.reduce((sum, c) => sum + c.score, 0) / source.chunks.length
                        const relevancePercent = (avgScore * 100).toFixed(0)
                        const relevanceColor = avgScore > 0.5 ? 'text-green-400' : avgScore > 0.3 ? 'text-yellow-400' : 'text-gray-500'
                        
                        return (
                          <div
                            key={idx}
                            className="group bg-dark-400/50 hover:bg-dark-400 rounded-lg p-3 border border-gray-800 hover:border-gray-700 transition-colors"
                          >
                            <div className="flex items-start gap-3">
                              {/* Source Icon */}
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                                source.isWeb ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'
                              }`}>
                                {source.isWeb ? <Globe className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                              </div>
                              
                              {/* Source Content */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-xs font-medium text-gray-300 truncate">
                                    [{idx + 1}] {source.name}
                                  </span>
                                  <span className={`text-xs font-mono ${relevanceColor}`}>
                                    {relevancePercent}%
                                  </span>
                                  {source.chunks.length > 1 && (
                                    <span className="text-xs text-gray-600">
                                      ({source.chunks.length} sections)
                                    </span>
                                  )}
                                </div>
                                
                                <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                                  {source.chunks[0].text}
                                </p>
                                
                                {source.url && (
                                  <a 
                                    href={source.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 mt-1"
                                  >
                                    Open link <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })()}
              
              {/* Model indicator */}
              {message.model && message.role === 'assistant' && (
                <div className="mt-2 text-xs text-gray-600">
                  Model: {message.model}
                </div>
              )}
            </div>

            {message.role === 'user' && (
              <div className="w-10 h-10 rounded-xl bg-gray-700 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-gray-300" />
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything..."
                rows={1}
                className="w-full bg-dark-300 border border-gray-800 rounded-xl px-4 py-3 pr-12 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500 resize-none"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="px-5 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl text-white font-medium transition-colors flex items-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2 text-center">
            AI may produce inaccurate information. Verify important facts.
          </p>
        </div>
      </div>
    </div>
  )
}


