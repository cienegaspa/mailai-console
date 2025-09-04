import { useState } from 'react'
import { XMarkIcon, AtSymbolIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface NewRunModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: any) => void
}

export default function NewRunModal({ isOpen, onClose, onSubmit }: NewRunModalProps) {
  const [formData, setFormData] = useState({
    question: '',
    accounts: [] as string[], // Array of selected account IDs
    after: '',
    before: '',
    domains: '',
    max_iters: 4,
    use_api_planner: false,
    polish_with_api: false,
  })

  // Mock connected accounts - will be replaced with real data
  const connectedAccounts = [
    { id: '1', email: 'tom@cienegaspa.com', status: 'connected' },
    { id: '2', email: 'rose@cienegaspa.com', status: 'connected' },
    { id: '3', email: 'tbwerz@gmail.com', status: 'disconnected' }
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const submitData = {
      ...formData,
      domains: formData.domains ? formData.domains.split(',').map(d => d.trim()) : undefined,
    }
    
    onSubmit(submitData)
    
    // Reset form
    setFormData({
      question: '',
      accounts: [],
      after: '',
      before: '',
      domains: '',
      max_iters: 4,
      use_api_planner: false,
      polish_with_api: false,
    })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Overlay */}
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />
        
        {/* Modal */}
        <div className="inline-block w-full max-w-md p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">New Question</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Question</label>
              <textarea
                value={formData.question}
                onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                className="input h-20 resize-none"
                placeholder="Enter your attorney question..."
                required
              />
            </div>

            <div>
              <label className="label">Gmail Accounts</label>
              <p className="text-sm text-gray-600 mb-4">
                <strong>Select accounts to search.</strong> Multiple accounts help ensure complete thread coverage and identify cross-account communications.
              </p>
              <div className="space-y-3">
                {connectedAccounts.map((account) => (
                  <label 
                    key={account.id} 
                    className={`flex items-center p-4 border-2 rounded-xl transition-all duration-200 cursor-pointer ${
                      formData.accounts.includes(account.id)
                        ? 'border-blue-200 bg-blue-50 shadow-sm'
                        : account.status === 'connected'
                        ? 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        : 'border-gray-100 bg-gray-50 cursor-not-allowed opacity-60'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={formData.accounts.includes(account.id)}
                      onChange={(e) => {
                        const accounts = e.target.checked
                          ? [...formData.accounts, account.id]
                          : formData.accounts.filter(id => id !== account.id)
                        setFormData({ ...formData, accounts })
                      }}
                      disabled={account.status !== 'connected'}
                      className="mr-4 h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div className={`p-2 rounded-full mr-3 ${account.status === 'connected' ? 'bg-green-100' : 'bg-gray-200'}`}>
                      <AtSymbolIcon className={`h-5 w-5 ${account.status === 'connected' ? 'text-green-600' : 'text-gray-400'}`} />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-gray-900">{account.email}</div>
                      <div className="flex items-center mt-1">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          account.status === 'connected' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {account.status === 'connected' ? '● Connected' : '○ Disconnected'}
                        </span>
                      </div>
                    </div>
                    {account.status !== 'connected' && (
                      <ExclamationCircleIcon className="h-5 w-5 text-gray-400" />
                    )}
                  </label>
                ))}
              </div>
              {formData.accounts.length === 0 && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700 font-medium">⚠️ Please select at least one account to continue.</p>
                </div>
              )}
              {formData.accounts.length > 0 && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-700">
                    ✓ {formData.accounts.length} account{formData.accounts.length > 1 ? 's' : ''} selected for comprehensive search
                  </p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">After Date</label>
                <input
                  type="date"
                  value={formData.after}
                  onChange={(e) => setFormData({ ...formData, after: e.target.value })}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Before Date</label>
                <input
                  type="date"
                  value={formData.before}
                  onChange={(e) => setFormData({ ...formData, before: e.target.value })}
                  className="input"
                />
              </div>
            </div>

            <div>
              <label className="label">Domains (comma-separated)</label>
              <input
                type="text"
                value={formData.domains}
                onChange={(e) => setFormData({ ...formData, domains: e.target.value })}
                className="input"
                placeholder="allergan.com, abbvie.com"
              />
            </div>

            <div>
              <label className="label">Max Iterations</label>
              <select
                value={formData.max_iters}
                onChange={(e) => setFormData({ ...formData, max_iters: parseInt(e.target.value) })}
                className="input"
              >
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.use_api_planner}
                  onChange={(e) => setFormData({ ...formData, use_api_planner: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Use API for query planning</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.polish_with_api}
                  onChange={(e) => setFormData({ ...formData, polish_with_api: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Polish summaries with API</span>
              </label>
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formData.accounts.length === 0}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Run
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}