import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { 
  PlusIcon, 
  CheckCircleIcon, 
  ExclamationCircleIcon,
  TrashIcon,
  AtSymbolIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface GmailAccount {
  account_id: string
  email: string
  display_name?: string
  status: 'connected' | 'disconnected' | 'error' | 'pending'
  connected_at?: string
  last_sync?: string
  total_messages?: number
  sync_error?: string
}

// API functions
const fetchAccounts = async (): Promise<GmailAccount[]> => {
  console.log('🔵 Fetching accounts...')
  
  try {
    const response = await fetch('http://127.0.0.1:5170/accounts')
    console.log('🔵 Fetch accounts response status:', response.status)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ Fetch accounts failed:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      })
      throw new Error(`Failed to fetch accounts: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log('🔵 Fetched accounts:', data)
    return data
  } catch (error) {
    console.error('❌ Fetch accounts error:', error)
    throw error
  }
}

const connectAccount = async (): Promise<string> => {
  console.log('🔵 Starting OAuth connection...')
  
  try {
    const response = await fetch('http://127.0.0.1:5170/auth/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    
    console.log('🔵 OAuth connect response status:', response.status)
    console.log('🔵 OAuth connect response headers:', Object.fromEntries(response.headers.entries()))
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ OAuth connect failed:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      })
      throw new Error(`Failed to initiate OAuth: ${response.status} ${response.statusText} - ${errorText}`)
    }
    
    const data = await response.json()
    console.log('🔵 OAuth connect success:', data)
    return data.auth_url
  } catch (error) {
    console.error('❌ OAuth connect error:', error)
    throw error
  }
}

const disconnectAccount = async (accountId: string): Promise<void> => {
  const response = await fetch(`http://127.0.0.1:5170/accounts/${accountId}/disconnect`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to disconnect account')
  }
}

const syncAccount = async (accountId: string): Promise<void> => {
  const response = await fetch(`http://127.0.0.1:5170/accounts/${accountId}/sync`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to sync account')
  }
}

export default function Accounts() {
  const [isConnecting, setIsConnecting] = useState(false)
  const queryClient = useQueryClient()

  // Real API query
  const { data: accounts, isLoading, error } = useQuery<GmailAccount[]>(
    'gmail-accounts', 
    fetchAccounts,
    { 
      refetchInterval: 30000,
      retry: 3,
      staleTime: 10000
    }
  )

  const handleConnectAccount = async () => {
    setIsConnecting(true)
    try {
      const authUrl = await connectAccount()
      // Redirect to Google OAuth
      window.location.href = authUrl
    } catch (error) {
      toast.error('Failed to start account connection')
      setIsConnecting(false)
    }
  }

  const handleDisconnectAccount = async (accountId: string, email: string) => {
    if (!confirm(`Are you sure you want to disconnect ${email}?`)) return
    
    try {
      await disconnectAccount(accountId)
      toast.success('Account disconnected')
      queryClient.invalidateQueries('gmail-accounts')
    } catch (error) {
      toast.error('Failed to disconnect account')
    }
  }

  const handleSyncAccount = async (accountId: string) => {
    try {
      await syncAccount(accountId)
      toast.success('Account synced successfully')
      queryClient.invalidateQueries('gmail-accounts')
    } catch (error) {
      toast.error('Sync failed')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'pending':
        return <ArrowPathIcon className="h-5 w-5 text-yellow-500 animate-spin" />
      default:
        return <ExclamationCircleIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected': return 'Connected'
      case 'error': return 'Error'
      case 'pending': return 'Connecting...'
      default: return 'Disconnected'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <ExclamationCircleIcon className="h-12 w-12 text-red-500" />
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900">Connection Error</h3>
          <p className="text-gray-600">Unable to load Gmail accounts. Please check your connection.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gmail Accounts</h1>
          <p className="text-gray-600">
            Manage your Gmail accounts for evidence analysis. Multiple accounts help ensure complete thread coverage.
          </p>
        </div>
        
        <button
          onClick={handleConnectAccount}
          disabled={isConnecting}
          className="btn-primary flex items-center space-x-2"
        >
          {isConnecting ? (
            <ArrowPathIcon className="h-5 w-5 animate-spin" />
          ) : (
            <PlusIcon className="h-5 w-5" />
          )}
          <span>{isConnecting ? 'Connecting...' : 'Connect Account'}</span>
        </button>
      </div>

      {/* OAuth Setup Notice */}
      {(!accounts || accounts.length === 0) && (
        <div className="border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <ExclamationCircleIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-blue-800">Setup Required</h4>
              <p className="text-sm text-blue-700 mt-1">
                To connect Gmail accounts, you need to configure Google OAuth credentials.
                <span className="font-medium"> Check the setup instructions below.</span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Accounts List */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Account
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Messages
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Sync
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {accounts?.map((account) => (
                <tr key={account.account_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-4">
                      <div className={`p-2 rounded-full ${account.status === 'connected' ? 'bg-green-100' : 'bg-gray-200'}`}>
                        <AtSymbolIcon className={`h-6 w-6 ${account.status === 'connected' ? 'text-green-600' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {account.email}
                        </p>
                        <p className="text-xs text-gray-500">
                          Connected {account.connected_at && new Date(account.connected_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(account.status)}
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        account.status === 'connected' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {getStatusText(account.status)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {account.total_messages?.toLocaleString() || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {account.last_sync ? new Date(account.last_sync).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">
                    <div className="flex items-center space-x-3">
                      {account.status === 'connected' && (
                        <button
                          onClick={() => handleSyncAccount(account.account_id)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Sync
                        </button>
                      )}
                      <button
                        onClick={() => handleDisconnectAccount(account.account_id, account.email)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Disconnect
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!accounts?.length && (
          <div className="text-center py-12">
            <AtSymbolIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No accounts connected</h3>
            <p className="mt-1 text-sm text-gray-500">
              Connect your Gmail accounts to start analyzing email evidence.
            </p>
            <div className="mt-6">
              <button
                onClick={handleConnectAccount}
                disabled={isConnecting}
                className="btn-primary"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Connect First Account
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Account Statistics */}
      {accounts && accounts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <AtSymbolIcon className="h-8 w-8 text-blue-500" />
              </div>
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {accounts.length}
                </div>
                <div className="text-sm text-gray-600">Connected Accounts</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-8 w-8 text-green-500" />
              </div>
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {accounts.filter(a => a.status === 'connected').length}
                </div>
                <div className="text-sm text-gray-600">Active</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ArrowPathIcon className="h-8 w-8 text-purple-500" />
              </div>
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {accounts.reduce((sum, a) => sum + (a.total_messages || 0), 0).toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Total Messages</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}