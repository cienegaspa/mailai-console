import { useState } from 'react'
import { 
  XMarkIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface ConnectIMAPModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (email: string) => void
}

const connectIMAPAccount = async (email: string, appPassword: string): Promise<any> => {
  const response = await fetch('http://127.0.0.1:5170/auth/connect-imap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, app_password: appPassword })
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Connection failed: ${response.status} ${response.statusText} - ${errorText}`)
  }
  
  return await response.json()
}

export default function ConnectIMAPModal({ isOpen, onClose, onSuccess }: ConnectIMAPModalProps) {
  const [step, setStep] = useState<'guide' | 'connect' | 'testing'>('guide')
  const [email, setEmail] = useState('')
  const [appPassword, setAppPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const handleConnect = async () => {
    if (!email || !appPassword) {
      toast.error('Please enter both email and app password')
      return
    }
    
    setIsLoading(true)
    setStep('testing')
    
    try {
      const result = await connectIMAPAccount(email, appPassword)
      
      if (result.success) {
        toast.success(`Successfully connected ${email}`)
        onSuccess(email)
        onClose()
        // Reset form
        setStep('guide')
        setEmail('')
        setAppPassword('')
      } else {
        throw new Error(result.error || 'Connection failed')
      }
    } catch (error) {
      console.error('IMAP connection error:', error)
      toast.error(error instanceof Error ? error.message : 'Connection failed')
      setStep('connect') // Go back to connect form
    } finally {
      setIsLoading(false)
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            Connect Gmail Account
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {step === 'guide' && (
            <div className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-blue-600" />
                  <h3 className="font-medium text-blue-900">Much Simpler Than OAuth!</h3>
                </div>
                <p className="text-sm text-blue-700 mt-2">
                  No Google Cloud Console setup, no verification videos, no complex configuration required.
                </p>
              </div>
              
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Quick Setup (2 minutes):</h3>
                <ol className="space-y-3 text-sm">
                  <li className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-medium">1</span>
                    <div>
                      <p className="font-medium">Enable 2-Factor Authentication</p>
                      <p className="text-gray-600">
                        Go to{' '}
                        <a 
                          href="https://myaccount.google.com/security" 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 inline-flex items-center"
                        >
                          Google Account Security
                          <ArrowTopRightOnSquareIcon className="h-3 w-3 ml-1" />
                        </a>
                        {' '}→ 2-Step Verification (skip if already enabled)
                      </p>
                    </div>
                  </li>
                  
                  <li className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-medium">2</span>
                    <div>
                      <p className="font-medium">Generate App Password</p>
                      <p className="text-gray-600">
                        In the same page → App passwords → Select app: <strong>Mail</strong> → Generate
                      </p>
                    </div>
                  </li>
                  
                  <li className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-medium">3</span>
                    <div>
                      <p className="font-medium">Copy the 16-character password</p>
                      <p className="text-gray-600">
                        It looks like: <code className="bg-gray-100 px-1 rounded">abcd efgh ijkl mnop</code>
                      </p>
                    </div>
                  </li>
                </ol>
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => setStep('connect')}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                >
                  I Have My App Password
                </button>
              </div>
            </div>
          )}
          
          {step === 'connect' && (
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Gmail Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tom@cienegaspa.com"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label htmlFor="appPassword" className="block text-sm font-medium text-gray-700">
                  App Password
                </label>
                <input
                  type="password"
                  id="appPassword"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  placeholder="abcd efgh ijkl mnop"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono"
                />
                <p className="mt-1 text-xs text-gray-500">
                  The 16-character password from Google App passwords (not your regular password)
                </p>
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setStep('guide')}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={handleConnect}
                  disabled={!email || !appPassword || isLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Connect Gmail
                </button>
              </div>
            </div>
          )}
          
          {step === 'testing' && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-sm text-gray-600">Testing Gmail connection...</p>
              <p className="text-xs text-gray-500 mt-1">This may take a few seconds</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}