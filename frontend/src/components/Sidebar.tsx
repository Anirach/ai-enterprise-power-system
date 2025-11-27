'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  MessageSquare, 
  Database, 
  Settings, 
  Zap,
  BookOpen,
  LayoutDashboard
} from 'lucide-react'

const navigation = [
  { name: 'Chat', href: '/', icon: MessageSquare },
  { name: 'Knowledge Base', href: '/knowledge', icon: Database },
  { name: 'Admin', href: '/admin', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-dark-400 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg gradient-text">AI Power</h1>
            <p className="text-xs text-gray-500">Knowledge System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>

      {/* Quick Links */}
      <div className="p-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Quick Links</p>
        <div className="space-y-2">
          <a
            href="/docs"
            target="_blank"
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-primary-400 transition-colors"
          >
            <BookOpen className="w-4 h-4" />
            API Docs
          </a>
          <a
            href="http://localhost:5678"
            target="_blank"
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-primary-400 transition-colors"
          >
            <LayoutDashboard className="w-4 h-4" />
            n8n Workflows
          </a>
        </div>
      </div>

      {/* Status */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-xs text-gray-500">System Online</span>
        </div>
      </div>
    </div>
  )
}


