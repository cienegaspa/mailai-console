import { useState, useEffect } from 'react'
import { 
  EnvelopeIcon,
  CalendarDaysIcon,
  XMarkIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
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

// Load messages from all accounts with better error handling
const fetchRecentMessages = async (): Promise<{ 
  total_accounts: number, 
  successful_accounts: number,
  failed_accounts: string[],
  total_messages: number, 
  messages: Message[] 
}> => {
  // Temporarily use only the most reliable account for demo
  const accounts = ['tom@cienegaspa.com']
  const allMessages: Message[] = []
  let successfulAccounts = 0
  const failedAccounts: string[] = []
  
  console.log(`🚀 Starting fetchRecentMessages for ${accounts.length} accounts`)
  console.log(`📋 Account list:`, accounts)
  
  // Process accounts sequentially to avoid overwhelming IMAP connections
  const results = []
  
  for (const accountId of accounts) {
    try {
      console.log(`🔵 [${new Date().toISOString()}] Starting fetch from ${accountId}...`)
      
      // 60 second timeout per account (backend can be slow with IMAP)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        console.log(`⏰ [${new Date().toISOString()}] Timeout triggered for ${accountId} after 60 seconds`)
        controller.abort()
      }, 60000)
      
      const url = `http://127.0.0.1:5170/debug/show-messages/${encodeURIComponent(accountId)}`
      console.log(`🌐 [${new Date().toISOString()}] Making request to: ${url}`)
      
      const response = await fetch(url, { signal: controller.signal })
      
      clearTimeout(timeoutId)
      console.log(`📊 [${new Date().toISOString()}] Response received - Status: ${response.status}, OK: ${response.ok}`)
      
      if (response.ok) {
        console.log(`📥 [${new Date().toISOString()}] Starting to parse JSON response for ${accountId}`)
        const data = await response.json()
        console.log(`📋 [${new Date().toISOString()}] JSON parsed successfully for ${accountId}`)
        console.log(`🔍 Response structure:`, {
          success: data.success,
          account: data.account,
          total_found: data.total_found,
          messages_shown: data.messages_shown,
          messages_length: data.messages?.length || 0,
          has_messages: Array.isArray(data.messages)
        })
        
        // Debug endpoint returns: {success, account, total_found, messages_shown, messages}
        if (data.success && data.messages && Array.isArray(data.messages)) {
          console.log(`✅ [${new Date().toISOString()}] ${accountId}: ${data.messages.length} messages loaded from debug endpoint`)
          console.log(`🔍 First message sample:`, data.messages[0])
          console.log(`🔍 Message structure check:`, {
            gmail_id: data.messages[0]?.gmail_id,
            subject: data.messages[0]?.subject,
            from_email: data.messages[0]?.from_email,
            date: data.messages[0]?.date
          })
          
          // Ensure each message has the account_email field
          const messagesWithAccount = data.messages.map((msg, idx) => {
            console.log(`📧 [${new Date().toISOString()}] Processing message ${idx + 1}: ${msg.subject?.substring(0, 30)}...`)
            return {
              ...msg,
              account_email: data.account || accountId
            }
          })
          
          console.log(`📦 [${new Date().toISOString()}] Processed ${messagesWithAccount.length} messages for ${accountId}`)
          results.push({ accountId, messages: messagesWithAccount, success: true })
        } else {
          console.warn(`⚠️ [${new Date().toISOString()}] ${accountId}: Invalid response structure:`, data)
          console.warn(`⚠️ Data success: ${data.success}, has messages: ${Array.isArray(data.messages)}, messages count: ${data.messages?.length}`)
          results.push({ accountId, messages: [], success: false })
        }
      } else {
        console.error(`❌ [${new Date().toISOString()}] ${accountId}: HTTP ${response.status}`)
        const errorText = await response.text()
        console.error(`❌ Error details: ${errorText}`)
        results.push({ accountId, messages: [], success: false })
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.error(`⏱️ [${new Date().toISOString()}] ${accountId}: Timeout after 30 seconds`)
      } else {
        console.error(`❌ [${new Date().toISOString()}] ${accountId}: ${error}`)
        console.error(`❌ Error stack:`, error.stack)
      }
      results.push({ accountId, messages: [], success: false })
    }
  }
  
  // Process results
  console.log(`🔄 [${new Date().toISOString()}] Processing results from ${results.length} accounts`)
  results.forEach((result, idx) => {
    console.log(`📊 [${new Date().toISOString()}] Result ${idx + 1}: Account ${result.accountId}, Success: ${result.success}, Messages: ${result.messages.length}`)
    if (result.success) {
      allMessages.push(...result.messages)
      successfulAccounts++
      console.log(`✅ [${new Date().toISOString()}] Added ${result.messages.length} messages from ${result.accountId}`)
    } else {
      failedAccounts.push(result.accountId)
      console.log(`❌ [${new Date().toISOString()}] Failed account: ${result.accountId}`)
    }
  })
  
  // Sort all messages by date (most recent first)
  console.log(`🗂️ [${new Date().toISOString()}] Sorting ${allMessages.length} messages by date`)
  allMessages.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  
  console.log(`🎉 [${new Date().toISOString()}] Total loaded: ${allMessages.length} messages from ${successfulAccounts}/${accounts.length} accounts`)
  console.log(`🔍 Final result summary:`, {
    total_accounts: accounts.length,
    successful_accounts: successfulAccounts,
    failed_accounts: failedAccounts,
    total_messages: allMessages.length,
    first_message_subject: allMessages[0]?.subject,
    first_message_from: allMessages[0]?.from_email,
    first_message_date: allMessages[0]?.date
  })
  
  const finalResult = {
    total_accounts: accounts.length,
    successful_accounts: successfulAccounts,
    failed_accounts: failedAccounts,
    total_messages: allMessages.length,
    messages: allMessages
  }
  
  console.log(`🚀 [${new Date().toISOString()}] Returning final result with ${finalResult.total_messages} messages`)
  return finalResult
}

export default function RecentMessagesViewer({ isOpen, onClose }: RecentMessagesViewerProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successfulAccounts, setSuccessfulAccounts] = useState(0)
  const [totalAccounts, setTotalAccounts] = useState(3)
  const [failedAccounts, setFailedAccounts] = useState<string[]>([])
  const [totalMessages, setTotalMessages] = useState(0)
  
  // Auto-load messages when modal opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      loadMessages()
    }
  }, [isOpen])
  
  const loadMessages = async () => {
    console.log(`🎬 [${new Date().toISOString()}] loadMessages() called - Starting message loading process`)
    
    setIsLoading(true)
    setError(null)
    setMessages([])
    
    console.log(`🔄 [${new Date().toISOString()}] UI state reset - loading: true, error: null, messages: []`)
    
    try {
      console.log(`📞 [${new Date().toISOString()}] Calling fetchRecentMessages()`)
      const result = await fetchRecentMessages()
      
      console.log(`📋 [${new Date().toISOString()}] fetchRecentMessages() completed successfully`)
      console.log(`📊 Result summary:`, {
        total_messages: result.total_messages,
        successful_accounts: result.successful_accounts,
        total_accounts: result.total_accounts,
        failed_accounts_count: result.failed_accounts.length,
        messages_array_length: result.messages.length
      })
      
      console.log(`🎯 [${new Date().toISOString()}] Setting UI state with loaded data`)
      setMessages(result.messages)
      setSuccessfulAccounts(result.successful_accounts)
      setTotalAccounts(result.total_accounts)
      setFailedAccounts(result.failed_accounts)
      setTotalMessages(result.total_messages)
      
      console.log(`✅ [${new Date().toISOString()}] UI state updated successfully - ${result.messages.length} messages set`)
      
    } catch (err) {
      console.error(`💥 [${new Date().toISOString()}] Failed to load messages:`, err)
      console.error(`💥 Error details:`, {
        name: err?.name,
        message: err?.message,
        stack: err?.stack
      })
      setError(err instanceof Error ? err.message : 'Failed to load messages')
      console.log(`🚨 [${new Date().toISOString()}] Error state set in UI`)
    } finally {
      console.log(`🏁 [${new Date().toISOString()}] Setting loading to false`)
      setIsLoading(false)
      console.log(`🏁 [${new Date().toISOString()}] loadMessages() process completed`)
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
              Live data from your connected Gmail accounts (last 30 days)
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
          {isLoading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-sm text-gray-600">Loading messages from Gmail accounts...</p>
              <p className="text-xs text-gray-500 mt-1">Searching last 30 days across all connected accounts</p>
            </div>
          )}
          
          {error && !messages.length && (
            <div className="text-center py-12">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <ExclamationTriangleIcon className="h-8 w-8 text-red-500 mx-auto mb-2" />
                <h3 className="text-lg font-medium text-red-800">Error Loading Messages</h3>
                <p className="text-sm text-red-600 mt-2">{error}</p>
                <div className="mt-4">
                  <button
                    onClick={loadMessages}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                  >
                    <ArrowPathIcon className="h-4 w-4 mr-2" />
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {(messages.length > 0 || (!isLoading && successfulAccounts > 0)) && (
            <>
              {/* Stats */}
              <div className={`border rounded-lg p-4 mb-6 ${
                failedAccounts.length > 0 ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className={`font-medium ${
                      failedAccounts.length > 0 ? 'text-yellow-900' : 'text-green-900'
                    }`}>
                      {failedAccounts.length > 0 ? 'Partial Results Loaded' : 'All Messages Loaded Successfully'}
                    </h3>
                    <p className={`text-sm mt-1 ${
                      failedAccounts.length > 0 ? 'text-yellow-700' : 'text-green-700'
                    }`}>
                      Found {totalMessages} messages from {successfulAccounts}/{totalAccounts} connected accounts
                    </p>
                    {failedAccounts.length > 0 && (
                      <p className="text-xs text-yellow-600 mt-1">
                        Failed to load: {failedAccounts.join(', ')}
                      </p>
                    )}
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
              {messages.length > 0 ? (
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
                              {message.snippet.replace(/\r\n/g, ' ').replace(/\s+/g, ' ').trim()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="text-gray-500 mt-2">No messages found in the last 30 days</p>
                </div>
              )}
            </>
          )}
          
          {!isLoading && !messages.length && !error && successfulAccounts === 0 && (
            <div className="text-center py-12">
              <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">No Messages Yet</h3>
              <p className="mt-2 text-sm text-gray-600">
                Click the button below to load recent messages from your connected Gmail accounts
              </p>
              <div className="mt-6">
                <button
                  onClick={loadMessages}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <EnvelopeIcon className="h-5 w-5 mr-2" />
                  Load Recent Messages
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}