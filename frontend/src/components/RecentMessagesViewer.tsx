import { useState } from 'react'
import { 
  EnvelopeIcon,
  CalendarDaysIcon,
  XMarkIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'

interface Message {
  gmail_id: string
  thread_id: string
  date: string
  from_email: string
  subject: string
  snippet: string
  account_email: string
}

interface RecentMessagesViewerProps {
  isOpen: boolean
  onClose: () => void
}

const fetchRecentMessages = async (): Promise<{ total_accounts: number, total_messages: number, messages: Message[] }> => {
  const response = await fetch('http://127.0.0.1:5170/accounts/recent-messages?days=1&limit_per_account=5')
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to fetch messages: ${response.status} ${response.statusText} - ${errorText}`)
  }
  
  return await response.json()
}

export default function RecentMessagesViewer({ isOpen, onClose }: RecentMessagesViewerProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [totalAccounts, setTotalAccounts] = useState(0)
  const [totalMessages, setTotalMessages] = useState(0)
  
  const loadMessages = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const result = await fetchRecentMessages()
      setMessages(result.messages)
      setTotalAccounts(result.total_accounts)
      setTotalMessages(result.total_messages)
    } catch (err) {
      console.error('Failed to load messages:', err)
      setError(err instanceof Error ? err.message : 'Failed to load messages')
    } finally {
      setIsLoading(false)
    }
  }
  
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return dateStr
    }
  }
  
  const getAccountColor = (email: string) => {
    const colors = [
      'bg-blue-100 text-blue-800',
      'bg-green-100 text-green-800', 
      'bg-purple-100 text-purple-800',
      'bg-orange-100 text-orange-800'
    ]
    const hash = email.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Recent Gmail Messages
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Live data from your connected Gmail accounts
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {!messages.length && !isLoading && !error && (
            <div className="text-center py-12">
              <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">View Recent Messages</h3>
              <p className="mt-2 text-sm text-gray-600">
                Fetch today's messages from all your connected Gmail accounts
              </p>
              <div className="mt-6">
                <button
                  onClick={loadMessages}
                  className="btn-primary"
                >
                  <EnvelopeIcon className="h-5 w-5 mr-2" />
                  Load Recent Messages
                </button>
              </div>
            </div>
          )}
          
          {isLoading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-sm text-gray-600">Loading messages from Gmail...</p>
              <p className="text-xs text-gray-500 mt-1">This may take a few seconds</p>
            </div>
          )}
          
          {error && (
            <div className="text-center py-12">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-lg font-medium text-red-800">Error Loading Messages</h3>
                <p className="text-sm text-red-600 mt-2">{error}</p>
                <div className="mt-4">
                  <button
                    onClick={loadMessages}
                    className="btn-primary"
                  >
                    <ArrowPathIcon className="h-5 w-5 mr-2" />
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {messages.length > 0 && (
            <>
              {/* Stats */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-blue-900">Live Gmail Data Retrieved</h3>
                    <p className="text-sm text-blue-700 mt-1">
                      Found {totalMessages} recent messages from {totalAccounts} connected accounts
                    </p>
                  </div>
                  <button
                    onClick={loadMessages}
                    disabled={isLoading}
                    className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  >
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
              
              {/* Messages List */}
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.gmail_id}
                    className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getAccountColor(message.account_email)}`}>
                            {message.account_email}
                          </span>
                          <span className="text-xs text-gray-500 flex items-center">
                            <CalendarDaysIcon className="h-3 w-3 mr-1" />
                            {formatDate(message.date)}
                          </span>
                        </div>
                        
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {message.subject || '(No Subject)'}
                        </h4>
                        
                        <p className="text-sm text-gray-600 mt-1">
                          From: {message.from_email}
                        </p>
                        
                        {message.snippet && (
                          <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                            {message.snippet}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {messages.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-gray-500">No messages found from today</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}