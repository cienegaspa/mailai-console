const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5170'

export interface RunCreateRequest {
  question: string
  after?: string
  before?: string
  domains?: string[]
  max_iters?: number
  use_api_planner?: boolean
  polish_with_api?: boolean
}

export interface Run {
  run_id: string
  created_at: string
  question: string
  status: string
  metrics?: {
    total_messages?: number
    total_threads?: number
    iterations?: number
    total_duration_ms?: number
  }
  duration_ms?: number
  eta_ms?: number
}

export interface RunDetail {
  run_id: string
  question: string
  params: Record<string, any>
  status: string
  eta_ms?: number
  stop_reason?: string
  models: Record<string, string>
  metrics?: Record<string, any>
}

export interface Query {
  iteration: number
  query_str: string
  rationale?: string
  hits: number
  new_msgs: number
  new_threads: number
  exec_ms?: number
}

export interface ThreadSummary {
  thread_id: string
  first_date?: string
  last_date?: string
  participants: string[]
  top_score: number
  summary_md: string
  bullets: Array<{
    text: string
    quote: string
    gmail_id: string
    thread_id: string
    date: string
  }>
}

// API functions
export async function fetchRuns(): Promise<Run[]> {
  const response = await fetch(`${API_BASE}/runs`)
  if (!response.ok) {
    throw new Error('Failed to fetch runs')
  }
  return response.json()
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const response = await fetch(`${API_BASE}/runs/${runId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch run')
  }
  return response.json()
}

export async function createRun(data: RunCreateRequest): Promise<{ run_id: string }> {
  const response = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })
  
  if (!response.ok) {
    throw new Error('Failed to create run')
  }
  
  return response.json()
}

export async function fetchRunQueries(runId: string): Promise<Query[]> {
  const response = await fetch(`${API_BASE}/runs/${runId}/queries`)
  if (!response.ok) {
    throw new Error('Failed to fetch queries')
  }
  return response.json()
}

export async function fetchRunThreads(runId: string): Promise<ThreadSummary[]> {
  const response = await fetch(`${API_BASE}/runs/${runId}/threads`)
  if (!response.ok) {
    throw new Error('Failed to fetch threads')
  }
  return response.json()
}

export async function fetchRunTerms(runId: string): Promise<Array<{
  iteration: number
  added_terms: string[]
  removed_terms: string[]
  evidence_terms: string[]
}>> {
  const response = await fetch(`${API_BASE}/runs/${runId}/terms`)
  if (!response.ok) {
    throw new Error('Failed to fetch terms')
  }
  return response.json()
}

export async function pauseRun(runId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/runs/${runId}/pause`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to pause run')
  }
  return response.json()
}

export async function resumeRun(runId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/runs/${runId}/resume`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to resume run')
  }
  return response.json()
}

export async function cancelRun(runId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/runs/${runId}/cancel`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to cancel run')
  }
  return response.json()
}

export async function createQA(runId: string, question: string, mode: string = 'cached'): Promise<{ qa_id: string }> {
  const response = await fetch(`${API_BASE}/runs/${runId}/qa`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      mode
    })
  })
  if (!response.ok) {
    throw new Error('Failed to create Q&A')
  }
  return response.json()
}

export async function fetchRunQA(runId: string): Promise<Array<{
  qa_id: string
  role: string
  text: string
  created_at: string
  mode?: string
  used_expansion?: boolean
  artifacts?: any
}>> {
  const response = await fetch(`${API_BASE}/runs/${runId}/qa`)
  if (!response.ok) {
    throw new Error('Failed to fetch Q&A')
  }
  return response.json()
}

// Server-Sent Events for real-time updates
export function subscribeToRunEvents(
  runId: string,
  onEvent: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/runs/${runId}/events`)
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onEvent(data)
    } catch (error) {
      console.error('Failed to parse SSE event:', error)
    }
  }
  
  eventSource.onerror = (event) => {
    console.error('SSE error:', event)
    if (onError) {
      onError(new Error('Server-sent events connection failed'))
    }
  }
  
  // Return cleanup function
  return () => {
    eventSource.close()
  }
}