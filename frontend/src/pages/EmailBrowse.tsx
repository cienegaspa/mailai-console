import { useState, useEffect } from 'react'
import { 
  EnvelopeIcon,
  CalendarDaysIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  PaperClipIcon
} from '@heroicons/react/24/outline'

interface Message {
  gmail_id: string
  thread_id: string
  date: string
  from_email: string
  to_emails?: string[]
  cc_emails?: string[]
  subject: string
  snippet: string
  body?: string
  account_email: string
  has_attachments?: boolean
  attachment_count?: number
  message_size?: number
  labels?: string[]
}

interface Account {
  email: string
  status: string
  total_messages_in_gmail?: number
  messages_downloaded?: number
  last_sync?: string
}

export default function EmailBrowse() {
  const [messages, setMessages] = useState<Message[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccount, setSelectedAccount] = useState<string>('all')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'subject' | 'sender'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(1)
  const [messagesPerPage] = useState(20)

  // Load accounts on component mount
  useEffect(() => {
    loadAccounts()
  }, [])

  // Load messages when account selection changes
  useEffect(() => {
    if (accounts.length > 0) {
      loadMessages()
    }
  }, [selectedAccount, accounts])

  const loadAccounts = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5170/accounts')
      if (response.ok) {
        const data = await response.json()
        setAccounts(data.accounts || [])
        if (data.accounts && data.accounts.length > 0) {
          setSelectedAccount(data.accounts[0].email)
        }
      }
    } catch (err) {
      setError('Failed to load accounts')
    }
  }

  const loadMessages = async () => {
    if (!selectedAccount || selectedAccount === 'all') return
    
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`http://127.0.0.1:5170/debug/show-messages/${encodeURIComponent(selectedAccount)}`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.messages) {
          setMessages(data.messages)
        } else {
          setError(data.error || 'Failed to load messages')
        }
      } else {
        setError('Failed to fetch messages')
      }
    } catch (err) {
      setError('Network error while loading messages')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleMessageExpansion = (messageId: string) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return dateStr
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Filter and sort messages
  const filteredMessages = messages.filter(message => {
    if (!searchTerm) return true
    const searchLower = searchTerm.toLowerCase()
    return (
      message.subject?.toLowerCase().includes(searchLower) ||
      message.from_email?.toLowerCase().includes(searchLower) ||
      message.snippet?.toLowerCase().includes(searchLower) ||
      message.body?.toLowerCase().includes(searchLower)
    )
  }).sort((a, b) => {
    let comparison = 0
    
    switch (sortBy) {
      case 'date':
        comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
        break
      case 'subject':
        comparison = (a.subject || '').localeCompare(b.subject || '')
        break
      case 'sender':
        comparison = (a.from_email || '').localeCompare(b.from_email || '')
        break
    }
    
    return sortOrder === 'desc' ? -comparison : comparison
  })

  // Pagination
  const totalPages = Math.ceil(filteredMessages.length / messagesPerPage)
  const startIndex = (currentPage - 1) * messagesPerPage
  const paginatedMessages = filteredMessages.slice(startIndex, startIndex + messagesPerPage)

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Email Browse</h1>
        <p className="text-gray-600">View and search through all downloaded messages</p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Account Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Account</label>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Accounts</option>
              {accounts.map(account => (
                <option key={account.email} value={account.email}>
                  {account.email} ({account.messages_downloaded || 0} messages)
                </option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <div className="relative">
              <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="Search messages..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [by, order] = e.target.value.split('-')
                setSortBy(by as 'date' | 'subject' | 'sender')
                setSortOrder(order as 'asc' | 'desc')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="date-desc">Date (Newest First)</option>
              <option value="date-asc">Date (Oldest First)</option>
              <option value="subject-asc">Subject (A-Z)</option>
              <option value="subject-desc">Subject (Z-A)</option>
              <option value="sender-asc">Sender (A-Z)</option>
              <option value="sender-desc">Sender (Z-A)</option>
            </select>
          </div>

          {/* Refresh */}
          <div className="flex items-end">
            <button
              onClick={loadMessages}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 flex items-center justify-center"
            >
              <ArrowPathIcon className={`h-5 w-5 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="text-2xl font-bold text-blue-600">{filteredMessages.length}</div>
          <div className="text-sm text-gray-600">Messages Found</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="text-2xl font-bold text-green-600">{accounts.length}</div>
          <div className="text-sm text-gray-600">Connected Accounts</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="text-2xl font-bold text-purple-600">{totalPages}</div>
          <div className="text-sm text-gray-600">Pages</div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading messages...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">Error</div>
          <div className="text-red-600 text-sm">{error}</div>
        </div>
      )}

      {/* Messages List */}
      {!isLoading && paginatedMessages.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          {paginatedMessages.map((message) => {
            const isExpanded = expandedMessages.has(message.gmail_id)
            return (
              <div
                key={message.gmail_id}
                className="border-b border-gray-200 last:border-b-0"
              >
                <div
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => toggleMessageExpansion(message.gmail_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {message.account_email}
                        </span>
                        <span className="text-xs text-gray-500 flex items-center">
                          <CalendarDaysIcon className="h-3 w-3 mr-1" />
                          {formatDate(message.date)}
                        </span>
                        {message.has_attachments && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                            <PaperClipIcon className="h-3 w-3 mr-1" />
                            {message.attachment_count || 1}
                          </span>
                        )}
                        {message.message_size && (
                          <span className="text-xs text-gray-500">
                            {formatFileSize(message.message_size)}
                          </span>
                        )}
                      </div>
                      
                      <h3 className="text-lg font-medium text-gray-900 mb-1">
                        {message.subject || '(No Subject)'}
                      </h3>
                      
                      <p className="text-sm text-gray-600 mb-2">
                        From: <span className="font-medium">{message.from_email}</span>
                      </p>
                      
                      {message.to_emails && message.to_emails.length > 0 && (
                        <p className="text-sm text-gray-600 mb-2">
                          To: {message.to_emails.join(', ')}
                        </p>
                      )}
                      
                      {!isExpanded && message.snippet && (
                        <p className="text-sm text-gray-500 line-clamp-2">
                          {message.snippet.replace(/\r\n/g, ' ').replace(/\s+/g, ' ').trim()}
                        </p>
                      )}
                      
                      {isExpanded && (
                        <div className="mt-4 border-t pt-4">
                          <h4 className="text-sm font-medium text-gray-900 mb-3">Full Message:</h4>
                          <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
                            {message.body || message.snippet || 'No content available'}
                          </div>
                          
                          {(message.message_size || message.thread_id || message.labels) && (
                            <div className="mt-4 text-xs text-gray-500 space-y-1">
                              {message.thread_id && (
                                <p>Thread ID: {message.thread_id}</p>
                              )}
                              <p>Message ID: {message.gmail_id}</p>
                              {message.labels && message.labels.length > 0 && (
                                <p>Labels: {message.labels.join(', ')}</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    
                    <div className="ml-4 flex items-center">
                      <span className="text-gray-400 text-lg">
                        {isExpanded ? '▲' : '▼'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {startIndex + 1} to {Math.min(startIndex + messagesPerPage, filteredMessages.length)} of {filteredMessages.length} messages
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  <ChevronLeftIcon className="h-4 w-4 mr-1" />
                  Previous
                </button>
                <span className="px-3 py-2 text-sm text-gray-700">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  Next
                  <ChevronRightIcon className="h-4 w-4 ml-1" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && paginatedMessages.length === 0 && (
        <div className="text-center py-12">
          <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Messages Found</h3>
          <p className="text-gray-600 mb-6">
            {searchTerm ? 'No messages match your search criteria.' : 'No messages have been downloaded yet.'}
          </p>
          {!searchTerm && (
            <button
              onClick={() => window.location.href = '/sync'}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Go to Sync Management
            </button>
          )}
        </div>
      )}
    </div>
  )
}