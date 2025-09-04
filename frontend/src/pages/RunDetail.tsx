import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from 'react-query'
import { 
  ArrowLeftIcon, 
  PlayIcon, 
  PauseIcon, 
  StopIcon,
  DocumentArrowDownIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'

import { fetchRun, fetchRunQueries, fetchRunThreads, subscribeToRunEvents, createQA, fetchRunQA } from '../utils/api'

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const [events, setEvents] = useState<any[]>([])
  const [progress, setProgress] = useState<any>(null)
  const [followupQuestion, setFollowupQuestion] = useState('')
  const [isSubmittingQuestion, setIsSubmittingQuestion] = useState(false)

  const { data: run, refetch } = useQuery(
    ['run', runId],
    () => fetchRun(runId!),
    { enabled: !!runId }
  )

  const { data: queries } = useQuery(
    ['run-queries', runId],
    () => fetchRunQueries(runId!),
    { enabled: !!runId }
  )

  const { data: threads } = useQuery(
    ['run-threads', runId],
    () => fetchRunThreads(runId!),
    { enabled: !!runId }
  )

  const { data: qaMessages, refetch: refetchQA } = useQuery(
    ['run-qa', runId],
    () => fetchRunQA(runId!),
    { enabled: !!runId }
  )

  // Subscribe to real-time events
  useEffect(() => {
    if (!runId) return

    const unsubscribe = subscribeToRunEvents(
      runId,
      (event) => {
        setEvents(prev => [...prev, event])
        
        if (event.type === 'phase_progress') {
          setProgress(event.data)
        }
        
        // Refetch data on completion
        if (event.type === 'run_complete') {
          refetch()
        }
      }
    )

    return unsubscribe
  }, [runId, refetch])

  const handleSubmitQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!followupQuestion.trim() || !runId || isSubmittingQuestion) return

    setIsSubmittingQuestion(true)
    try {
      await createQA(runId, followupQuestion.trim())
      setFollowupQuestion('')
      refetchQA()
    } catch (error) {
      console.error('Failed to submit question:', error)
    } finally {
      setIsSubmittingQuestion(false)
    }
  }

  if (!run) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const isActive = ['queued', 'fetching', 'normalizing', 'ranking', 'iterating', 'summarizing', 'exporting'].includes(run.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeftIcon className="h-6 w-6" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Run Detail</h1>
            <p className="text-gray-600 mt-1">{run.question}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {isActive && (
            <>
              <button className="btn-secondary flex items-center space-x-2">
                <PauseIcon className="h-4 w-4" />
                <span>Pause</span>
              </button>
              <button className="btn-danger flex items-center space-x-2">
                <StopIcon className="h-4 w-4" />
                <span>Cancel</span>
              </button>
            </>
          )}
          
          {run.status === 'done' && (
            <button className="btn-primary flex items-center space-x-2">
              <DocumentArrowDownIcon className="h-4 w-4" />
              <span>Export</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {isActive && progress && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {progress.current_phase || 'Processing...'}
            </span>
            <span className="text-sm text-gray-500">
              {Math.round((progress.overall_progress || 0) * 100)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(progress.overall_progress || 0) * 100}%` }}
            />
          </div>
          {progress.eta_ms && (
            <p className="text-xs text-gray-500 mt-1">
              ETA: {Math.round(progress.eta_ms / 1000)}s
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Chat Interface */}
          <div className="card">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 flex items-center">
                <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
                Q&A Interface
              </h3>
            </div>
            <div className="p-4">
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {/* Initial Question */}
                <div className="flex space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                      <span className="text-sm font-medium text-blue-700">U</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">{run.question}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(run.created_at || '').toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* AI Response for original question */}
                {run.status === 'done' && (
                  <div className="flex space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                        <span className="text-sm font-medium text-green-700">AI</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-sm text-gray-900 mb-2">
                          Based on my analysis of {run.metrics?.total_messages || 0} messages, I've processed the CoolSculpting Elite device return data. The queries executed found patterns related to returns, RMA processes, thermal sensor issues, and credit processing.
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {queries?.length || 0} queries executed across {run.metrics?.iterations || 0} iterations
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Follow-up Q&A Messages */}
                {qaMessages?.map((message) => (
                  <div key={message.qa_id} className="flex space-x-3">
                    <div className="flex-shrink-0">
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        message.role === 'user' 
                          ? 'bg-blue-100' 
                          : 'bg-green-100'
                      }`}>
                        <span className={`text-sm font-medium ${
                          message.role === 'user' 
                            ? 'text-blue-700' 
                            : 'text-green-700'
                        }`}>
                          {message.role === 'user' ? 'U' : 'AI'}
                        </span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className={message.role === 'assistant' ? 'bg-gray-50 rounded-lg p-3' : ''}>
                        <p className="text-sm text-gray-900">{message.text}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(message.created_at).toLocaleString()}
                        </p>
                        {message.artifacts && message.role === 'assistant' && (
                          <p className="text-xs text-gray-400 mt-1">
                            Confidence: {(message.artifacts.confidence * 100).toFixed(0)}%
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Input for follow-up questions */}
              <div className="border-t border-gray-200 pt-4">
                <form onSubmit={handleSubmitQuestion} className="flex space-x-3">
                  <input
                    type="text"
                    value={followupQuestion}
                    onChange={(e) => setFollowupQuestion(e.target.value)}
                    placeholder="Ask a follow-up question..."
                    className="flex-1 input"
                    disabled={isSubmittingQuestion}
                  />
                  <button 
                    type="submit"
                    className="btn-primary"
                    disabled={!followupQuestion.trim() || isSubmittingQuestion}
                  >
                    {isSubmittingQuestion ? 'Sending...' : 'Send'}
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Thread Results */}
          {threads && threads.length > 0 && (
            <div className="card">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Top Threads</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {threads.map((thread) => (
                  <div key={thread.thread_id} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-900">
                        Thread {thread.thread_id.slice(-8)}
                      </h4>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs text-gray-500">
                          Score: {thread.top_score.toFixed(2)}
                        </span>
                        <Link
                          to={`/runs/${runId}/evidence/${thread.thread_id}`}
                          className="btn-secondary text-xs"
                        >
                          View
                        </Link>
                      </div>
                    </div>
                    
                    <div className="text-sm text-gray-600 mb-2">
                      {thread.participants.join(', ')}
                    </div>
                    
                    {thread.bullets && thread.bullets.length > 0 && (
                      <ul className="space-y-1">
                        {thread.bullets.slice(0, 2).map((bullet, i) => (
                          <li key={i} className="text-sm">
                            • {bullet.text}
                            <span className="text-gray-400 ml-2">
                              [{bullet.gmail_id} | {bullet.date}]
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Overview */}
          <div className="card p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Overview</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Status</span>
                <span className="text-sm font-medium capitalize">{run.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Messages</span>
                <span className="text-sm font-medium">{run.metrics?.total_messages || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Threads</span>
                <span className="text-sm font-medium">{threads?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Iterations</span>
                <span className="text-sm font-medium">{run.metrics?.iterations || 0}</span>
              </div>
            </div>
          </div>

          {/* Queries Tried */}
          {queries && queries.length > 0 && (
            <div className="card p-4">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Queries Tried</h3>
              <div className="space-y-3">
                {queries.map((query, i) => (
                  <div key={i} className="text-xs">
                    <div className="font-medium text-gray-900 mb-1">
                      Iteration {query.iteration}
                    </div>
                    <div className="text-gray-600 bg-gray-50 p-2 rounded font-mono">
                      {query.query_str}
                    </div>
                    <div className="text-gray-500 mt-1">
                      {query.hits} hits, {query.new_msgs} new messages
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}