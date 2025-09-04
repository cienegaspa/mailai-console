import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from 'react-query'
import { PlusIcon, PlayIcon, ClockIcon, CheckCircleIcon, ExclamationCircleIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import { fetchRuns, createRun } from '../utils/api'
import NewRunModal from '../components/NewRunModal'

interface Run {
  run_id: string
  created_at: string
  question: string
  status: string
  metrics?: {
    total_messages?: number
    total_threads?: number
    iterations?: number
  }
  duration_ms?: number
  eta_ms?: number
}

export default function RunsList() {
  const [showNewRunModal, setShowNewRunModal] = useState(false)
  
  const { data: runs, isLoading, refetch } = useQuery<Run[]>('runs', fetchRuns, {
    refetchInterval: 5000, // Poll every 5 seconds
  })

  const handleCreateRun = async (runData: any) => {
    try {
      await createRun(runData)
      toast.success('Run created successfully!')
      setShowNewRunModal(false)
      refetch()
    } catch (error) {
      toast.error('Failed to create run')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'failed':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      case 'queued':
      case 'fetching':
      case 'normalizing':
      case 'ranking':
      case 'iterating':
      case 'summarizing':
      case 'exporting':
        return <PlayIcon className="h-5 w-5 text-blue-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`
    }
    return `${seconds}s`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Runs</h1>
          <p className="text-gray-600">Gmail evidence analysis runs</p>
        </div>
        
        <button
          onClick={() => setShowNewRunModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <PlusIcon className="h-5 w-5" />
          <span>New Question</span>
        </button>
      </div>

      {/* Runs table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Question
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Messages
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Threads
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs?.map((run) => (
                <tr key={run.run_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="max-w-md">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {run.question}
                      </p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(run.status)}
                      <span className="text-sm text-gray-900 capitalize">
                        {run.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {run.metrics?.total_messages || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {run.metrics?.total_threads || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatDuration(run.duration_ms)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(run.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">
                    <Link
                      to={`/runs/${run.run_id}`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {!runs?.length && (
          <div className="text-center py-12">
            <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No runs</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating your first Gmail evidence analysis.
            </p>
            <div className="mt-6">
              <button
                onClick={() => setShowNewRunModal(true)}
                className="btn-primary"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                New Question
              </button>
            </div>
          </div>
        )}
      </div>

      {/* New Run Modal */}
      <NewRunModal
        isOpen={showNewRunModal}
        onClose={() => setShowNewRunModal(false)}
        onSubmit={handleCreateRun}
      />
    </div>
  )
}