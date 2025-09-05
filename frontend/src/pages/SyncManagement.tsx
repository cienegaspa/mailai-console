import { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import FilterManagement from '../components/FilterManagement'
import { 
  ArrowPathIcon, 
  PlayIcon, 
  PauseIcon, 
  StopIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  EnvelopeIcon,
  ServerIcon,
  FunnelIcon,
  EyeIcon,
  ChartBarIcon,
  InboxIcon,
  CloudArrowDownIcon,
  Cog6ToothIcon,
  BoltIcon
} from '@heroicons/react/24/outline'

interface AccountSyncStatus {
  email: string
  status: 'idle' | 'syncing' | 'paused' | 'error' | 'completed'
  total_in_gmail?: number
  downloaded_locally: number
  last_sync?: string
  sync_progress?: {
    current: number
    total: number
    rate: string
    eta: string
    phase: string
  }
  error_message?: string
}

interface DomainFilter {
  id: number
  account_email: string
  filter_name: string
  domains: string[]
  include_from: boolean
  include_to: boolean
  include_cc: boolean
  date_after?: string
  date_before?: string
  is_active: boolean
  estimated_count: number
  last_tested?: string
  created_at: string
  updated_at: string
}

interface SyncHistory {
  id: number
  account_email: string
  filter_id?: number
  filter_name?: string
  sync_type: string
  total_messages_found: number
  messages_downloaded: number
  messages_skipped: number
  started_at: string
  completed_at?: string
  duration_seconds?: number
  status: string
  error_message?: string
}

export default function SyncManagement() {
  const [activeView, setActiveView] = useState<'status' | 'filters' | 'history'>('status')
  const [accounts, setAccounts] = useState<AccountSyncStatus[]>([])
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedFilter, setSelectedFilter] = useState<DomainFilter | null>(null)
  const [showFilteredSyncModal, setShowFilteredSyncModal] = useState(false)
  
  const [globalStats, setGlobalStats] = useState({
    totalAccounts: 0,
    totalMessages: 0,
    totalSynced: 0,
    lastGlobalSync: null as string | null
  })

  useEffect(() => {
    loadAccountStatus()
    // Set up polling for sync status updates
    const interval = setInterval(loadAccountStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedAccount && activeView === 'history') {
      loadSyncHistory()
    }
  }, [selectedAccount, activeView])

  const loadAccountStatus = async () => {
    try {
      const [accountsRes, statsRes] = await Promise.all([
        fetch('/api/sync/accounts-status'),
        fetch('/api/sync/global-stats')
      ])

      if (accountsRes.ok) {
        const accountsData = await accountsRes.json()
        const accountsList = accountsData.accounts || []
        setAccounts(accountsList)
        
        // Auto-select first account if none selected
        if (!selectedAccount && accountsList.length > 0) {
          setSelectedAccount(accountsList[0].email)
        }
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setGlobalStats(statsData)
      }
    } catch (err) {
      console.error('Error loading sync status:', err)
    }
  }

  const loadSyncHistory = async () => {
    if (!selectedAccount) return
    
    try {
      const response = await fetch(`/api/sync/history/${encodeURIComponent(selectedAccount)}`)
      if (response.ok) {
        const data = await response.json()
        setSyncHistory(data)
      }
    } catch (err) {
      console.error('Error loading sync history:', err)
    }
  }

  const startFilteredSync = async (filter: DomainFilter) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/sync/start-filtered', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_email: filter.account_email,
          filter_id: filter.id,
          sync_type: 'filtered',
          batch_size: 50,
          max_messages: 10000
        })
      })

      if (response.ok) {
        const data = await response.json()
        setSelectedFilter(null)
        setShowFilteredSyncModal(false)
        loadAccountStatus()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to start filtered sync')
      }
    } catch (err) {
      setError('Network error while starting sync')
    } finally {
      setIsLoading(false)
    }
  }

  const startSync = async (accountEmail: string, syncType: 'incremental' | 'full' = 'incremental') => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/sync/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_email: accountEmail,
          sync_type: syncType,
          batch_size: 50,
          max_messages: syncType === 'incremental' ? 1000 : null
        })
      })

      if (response.ok) {
        loadAccountStatus()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to start sync')
      }
    } catch (err) {
      setError('Network error while starting sync')
    } finally {
      setIsLoading(false)
    }
  }

  const pauseSync = async (accountEmail: string) => {
    try {
      const response = await fetch('/api/sync/pause', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_email: accountEmail })
      })
      if (response.ok) loadAccountStatus()
    } catch (err) {
      console.error('Error pausing sync:', err)
    }
  }

  const stopSync = async (accountEmail: string) => {
    try {
      const response = await fetch('/api/sync/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_email: accountEmail })
      })
      if (response.ok) loadAccountStatus()
    } catch (err) {
      console.error('Error stopping sync:', err)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return 'Invalid date'
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`
    if (minutes > 0) return `${minutes}m ${secs}s`
    return `${secs}s`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'syncing':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'error':
      case 'failed':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
      case 'paused':
        return <PauseIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'syncing': 
      case 'running': 
        return 'bg-blue-100 text-blue-800'
      case 'completed': 
        return 'bg-green-100 text-green-800'
      case 'error': 
      case 'failed': 
        return 'bg-red-100 text-red-800'
      case 'paused': 
        return 'bg-yellow-100 text-yellow-800'
      default: 
        return 'bg-gray-100 text-gray-800'
    }
  }

  const renderAccountSelector = () => (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Select Account
      </label>
      <select
        value={selectedAccount}
        onChange={(e) => setSelectedAccount(e.target.value)}
        className="block w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {accounts.map((account) => (
          <option key={account.email} value={account.email}>
            {account.email}
          </option>
        ))}
      </select>
    </div>
  )

  const renderSyncStatus = () => (
    <div className="space-y-6">
      {/* Global Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg mr-4">
              <InboxIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{globalStats.totalAccounts}</div>
              <div className="text-sm text-gray-600">Connected Accounts</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg mr-4">
              <CloudArrowDownIcon className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {globalStats.totalSynced.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600">Messages Downloaded</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg mr-4">
              <ArrowPathIcon className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {globalStats.totalMessages.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600">Total Available</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg mr-4">
              <ClockIcon className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-gray-900">Last Sync</div>
              <div className="text-sm text-gray-600">{formatDate(globalStats.lastGlobalSync)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Account Sync Status */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Account Sync Status</h2>
        </div>

        <div className="divide-y divide-gray-200">
          {accounts.map((account) => (
            <div key={account.email} className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(account.status)}
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{account.email}</h3>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(account.status)}`}>
                        {account.status.charAt(0).toUpperCase() + account.status.slice(1)}
                      </span>
                      <span className="text-sm text-gray-500">
                        Last sync: {formatDate(account.last_sync)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {account.status === 'syncing' && (
                    <>
                      <button
                        onClick={() => pauseSync(account.email)}
                        className="px-3 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 flex items-center text-sm"
                      >
                        <PauseIcon className="h-4 w-4 mr-1" />
                        Pause
                      </button>
                      <button
                        onClick={() => stopSync(account.email)}
                        className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 flex items-center text-sm"
                      >
                        <StopIcon className="h-4 w-4 mr-1" />
                        Stop
                      </button>
                    </>
                  )}

                  {account.status !== 'syncing' && (
                    <>
                      <button
                        onClick={() => {
                          setSelectedAccount(account.email)
                          setShowFilteredSyncModal(true)
                        }}
                        disabled={isLoading}
                        className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 flex items-center text-sm"
                      >
                        <FunnelIcon className="h-4 w-4 mr-1" />
                        Filtered Sync
                      </button>
                      <button
                        onClick={() => startSync(account.email, 'incremental')}
                        disabled={isLoading}
                        className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 flex items-center text-sm"
                      >
                        <PlayIcon className="h-4 w-4 mr-1" />
                        Sync New
                      </button>
                      <button
                        onClick={() => startSync(account.email, 'full')}
                        disabled={isLoading}
                        className="px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 flex items-center text-sm"
                      >
                        <ArrowPathIcon className="h-4 w-4 mr-1" />
                        Full Sync
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Progress Information */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-gray-700 mb-1">Available in Gmail</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {account.total_in_gmail?.toLocaleString() || 'Unknown'}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-gray-700 mb-1">Downloaded Locally</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {account.downloaded_locally.toLocaleString()}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-gray-700 mb-1">Completion</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {account.total_in_gmail 
                      ? `${Math.round((account.downloaded_locally / account.total_in_gmail) * 100)}%`
                      : 'N/A'
                    }
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              {account.total_in_gmail && account.total_in_gmail > 0 && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                    <span>Sync Progress</span>
                    <span>{account.downloaded_locally} / {account.total_in_gmail} messages</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.min((account.downloaded_locally / account.total_in_gmail) * 100, 100)}%`
                      }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Active Sync Progress */}
              {account.status === 'syncing' && account.sync_progress && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm font-medium text-blue-900">
                      {account.sync_progress.phase}
                    </div>
                    <div className="text-sm text-blue-700">
                      {account.sync_progress.rate} • ETA: {account.sync_progress.eta}
                    </div>
                  </div>
                  {account.sync_progress.total > 0 && (
                    <div className="w-full bg-blue-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min((account.sync_progress.current / account.sync_progress.total) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                  )}
                  <div className="text-xs text-blue-600 mt-1">
                    {account.sync_progress.current} / {account.sync_progress.total} processed
                  </div>
                </div>
              )}

              {/* Error Message */}
              {account.status === 'error' && account.error_message && (
                <div className="bg-red-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-red-900 mb-1">Error Details</div>
                  <div className="text-sm text-red-700">{account.error_message}</div>
                </div>
              )}
            </div>
          ))}
        </div>

        {accounts.length === 0 && (
          <div className="p-12 text-center">
            <InboxIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Accounts Found</h3>
            <p className="text-gray-600 mb-6">Connect a Gmail account to start syncing messages.</p>
            <button
              onClick={() => window.location.href = '/accounts'}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Go to Accounts
            </button>
          </div>
        )}
      </div>
    </div>
  )

  const renderSyncHistory = () => (
    <div className="space-y-6">
      {renderAccountSelector()}
      
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Sync History</h2>
          <p className="text-sm text-gray-600 mt-1">Recent sync operations for {selectedAccount}</p>
        </div>

        <div className="divide-y divide-gray-200">
          {syncHistory.length === 0 ? (
            <div className="p-12 text-center">
              <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Sync History</h3>
              <p className="text-gray-600">No sync operations found for this account.</p>
            </div>
          ) : (
            syncHistory.map((sync) => (
              <div key={sync.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {getStatusIcon(sync.status)}
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900">
                            {sync.filter_name || `${sync.sync_type.charAt(0).toUpperCase() + sync.sync_type.slice(1)} Sync`}
                          </span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(sync.status)}`}>
                            {sync.status.charAt(0).toUpperCase() + sync.status.slice(1)}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600">
                          {formatDate(sync.started_at)}
                          {sync.completed_at && ` - ${formatDate(sync.completed_at)}`}
                          {sync.duration_seconds && ` (${formatDuration(sync.duration_seconds)})`}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                      <div className="text-sm">
                        <span className="font-medium text-gray-700">Found:</span>
                        <span className="ml-1 text-gray-900">{sync.total_messages_found.toLocaleString()}</span>
                      </div>
                      <div className="text-sm">
                        <span className="font-medium text-gray-700">Downloaded:</span>
                        <span className="ml-1 text-gray-900">{sync.messages_downloaded.toLocaleString()}</span>
                      </div>
                      <div className="text-sm">
                        <span className="font-medium text-gray-700">Skipped:</span>
                        <span className="ml-1 text-gray-900">{sync.messages_skipped.toLocaleString()}</span>
                      </div>
                    </div>

                    {sync.error_message && (
                      <div className="mt-3 p-3 bg-red-50 rounded-md">
                        <div className="text-sm text-red-800">{sync.error_message}</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Sync Management</h1>
            <p className="text-gray-600 mt-1">Monitor and control email message synchronization with advanced filtering</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
              <div className="text-red-800 font-medium">Error</div>
            </div>
            <div className="text-red-600 text-sm mt-1">{error}</div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveView('status')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeView === 'status'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <ServerIcon className="h-4 w-4" />
                <span>Sync Status</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('filters')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeView === 'filters'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <FunnelIcon className="h-4 w-4" />
                <span>Domain Filters</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('history')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeView === 'history'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <ChartBarIcon className="h-4 w-4" />
                <span>Sync History</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeView === 'status' && renderSyncStatus()}
          {activeView === 'filters' && selectedAccount && (
            <FilterManagement 
              accountEmail={selectedAccount} 
              onFilterSelected={(filter) => {
                setSelectedFilter(filter)
                setShowFilteredSyncModal(true)
              }}
            />
          )}
          {activeView === 'filters' && !selectedAccount && renderAccountSelector()}
          {activeView === 'history' && renderSyncHistory()}
        </div>

        {/* Filtered Sync Modal */}
        {showFilteredSyncModal && selectedFilter && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Start Filtered Sync</h3>
                <button
                  onClick={() => {
                    setShowFilteredSyncModal(false)
                    setSelectedFilter(null)
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filter</label>
                  <div className="text-sm text-gray-900">{selectedFilter.filter_name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Domains: {selectedFilter.domains.join(', ')}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Messages</label>
                  <div className="text-2xl font-bold text-blue-600">
                    {selectedFilter.estimated_count.toLocaleString()}
                  </div>
                </div>

                <div className="bg-blue-50 rounded-md p-3">
                  <div className="text-sm text-blue-800">
                    This will sync only messages matching the selected domain filter. 
                    The operation will run in the background and you can monitor progress in the sync status tab.
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 mt-6">
                <button
                  onClick={() => {
                    setShowFilteredSyncModal(false)
                    setSelectedFilter(null)
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => startFilteredSync(selectedFilter)}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
                >
                  {isLoading ? (
                    <>
                      <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <BoltIcon className="h-4 w-4 mr-2" />
                      Start Filtered Sync
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}