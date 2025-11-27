'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ text: string; score: number }>
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [useRag, setUseRag] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      return 'http://localhost:8000'
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

    try {
      const response = await fetch(`${getApiUrl()}/api/chat/`, {
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

      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.message,
        sources: data.sources
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please make sure the backend is running and Ollama has models loaded.'
      }])
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
          <div className="flex items-center gap-3">
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
            
            <div className={`max-w-2xl ${message.role === 'user' ? 'order-first' : ''}`}>
              <div
                className={`rounded-2xl px-5 py-4 ${
                  message.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-dark-300 border border-gray-800'
                }`}
              >
                <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
                  {message.content}
                </ReactMarkdown>
              </div>
              
              {message.sources && message.sources.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Sources</p>
                  {message.sources.map((source, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-gray-400 bg-dark-400 rounded-lg p-3 border border-gray-800"
                    >
                      <p className="line-clamp-2">{source.text}</p>
                      <p className="text-gray-600 mt-1">Relevance: {(source.score * 100).toFixed(1)}%</p>
                    </div>
                  ))}
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

        {isLoading && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-dark-300 border border-gray-800 rounded-2xl px-5 py-4">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full typing-dot"></div>
              </div>
            </div>
          </div>
        )}

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


