import { useState } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'

interface NewRunModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: any) => void
}

export default function NewRunModal({ isOpen, onClose, onSubmit }: NewRunModalProps) {
  const [formData, setFormData] = useState({
    question: '',
    after: '',
    before: '',
    domains: '',
    max_iters: 4,
    use_api_planner: false,
    polish_with_api: false,
  })

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
                className="btn-primary"
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