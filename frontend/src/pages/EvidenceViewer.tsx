import { useParams, Link } from 'react-router-dom'
import { ArrowLeftIcon, EnvelopeIcon, CalendarIcon } from '@heroicons/react/24/outline'

export default function EvidenceViewer() {
  const { runId, threadId } = useParams<{ runId: string; threadId: string }>()

  // Mock data for now
  const mockMessages = [
    {
      gmail_id: 'G-001',
      date: '2025-02-01T10:30:00Z',
      from_email: 'clinic.manager@example.com',
      subject: 'CoolSculpting Elite Return Request - Machine Serial CS-2024-001',
      body: `Dear Returns Team,

We need to return our CoolSculpting Elite machine (Serial: CS-2024-001) purchased in December 2024. The unit has been experiencing consistent temperature regulation issues that make it unsafe for patient treatments.

We've documented multiple instances where the machine won't process treatments without the P3 protocol, but even with P3 the cooling is erratic. Our technician reports the system shows "Error Code E-47" repeatedly.

Please advise on the RMA process and return shipping requirements.

Best regards,
Dr. Sarah Wilson
Aesthetic Wellness Clinic`,
      highlights: [
        'CoolSculpting Elite machine (Serial: CS-2024-001)',
        'temperature regulation issues',
        'Error Code E-47'
      ]
    },
    {
      gmail_id: 'G-002',
      date: '2025-02-02T14:15:00Z',
      from_email: 'returns@allergan.com',
      subject: 'RE: CoolSculpting Elite Return Request - RMA#: RMA-2025-0847',
      body: `Dr. Wilson,

Thank you for contacting us regarding your CoolSculpting Elite unit CS-2024-001.

I've created RMA#: RMA-2025-0847 for your return. Please note:

1. Return authorization expires in 30 days
2. Machine must be returned in original packaging or equivalent protective crate
3. All accessories and documentation must be included
4. Return shipping label will be provided - DO NOT ship without approved label

The unit will be inspected upon receipt. If the issues are confirmed as manufacturing defects, you'll receive a full credit.

RMA Specialist
Allergan Aesthetics Returns Department`,
      highlights: [
        'RMA#: RMA-2025-0847',
        'Return authorization expires in 30 days',
        'manufacturing defects'
      ]
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link to={`/runs/${runId}`} className="text-gray-400 hover:text-gray-600">
          <ArrowLeftIcon className="h-6 w-6" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evidence Viewer</h1>
          <p className="text-gray-600">Thread {threadId?.slice(-8)}</p>
        </div>
      </div>

      {/* Thread Info */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Thread Information</h3>
            <p className="text-sm text-gray-600">
              {mockMessages.length} messages • 
              {mockMessages.map(m => m.from_email.split('@')[1]).filter((v, i, a) => a.indexOf(v) === i).join(', ')}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">
              {new Date(mockMessages[0]?.date).toLocaleDateString()} - {new Date(mockMessages[mockMessages.length - 1]?.date).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="space-y-4">
        {mockMessages.map((message) => (
          <div key={message.gmail_id} className="card">
            {/* Message Header */}
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  <EnvelopeIcon className="h-5 w-5 text-gray-400 mt-1" />
                  <div>
                    <h4 className="font-medium text-gray-900">{message.subject}</h4>
                    <p className="text-sm text-gray-600">From: {message.from_email}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <CalendarIcon className="h-4 w-4" />
                  <span>{new Date(message.date).toLocaleString()}</span>
                </div>
              </div>
              
              <div className="mt-2 text-xs text-gray-500">
                Gmail ID: {message.gmail_id}
              </div>
            </div>

            {/* Message Body */}
            <div className="p-4">
              <div className="prose prose-sm max-w-none">
                {message.body.split('\n').map((line, i) => {
                  let processedLine = line
                  
                  // Highlight important phrases
                  message.highlights.forEach(highlight => {
                    if (processedLine.includes(highlight)) {
                      processedLine = processedLine.replace(
                        highlight,
                        `<mark class="bg-yellow-200 px-1 rounded">${highlight}</mark>`
                      )
                    }
                  })
                  
                  return (
                    <p 
                      key={i} 
                      className="mb-2" 
                      dangerouslySetInnerHTML={{ __html: processedLine || '<br/>' }}
                    />
                  )
                })}
              </div>
            </div>

            {/* Extracted Citations */}
            <div className="px-4 pb-4">
              <h5 className="text-sm font-medium text-gray-900 mb-2">Key Citations from this Message:</h5>
              <div className="space-y-1">
                {message.highlights.map((highlight, i) => (
                  <div key={i} className="text-xs bg-blue-50 border border-blue-200 rounded p-2">
                    <span className="font-mono text-blue-800">"{highlight}"</span>
                    <span className="text-gray-600 ml-2">
                      [{message.gmail_id} | {threadId} | {new Date(message.date).toISOString().split('T')[0]}]
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex justify-center">
        <a
          href={`mailto:${mockMessages[0]?.from_email}?subject=Re: ${mockMessages[0]?.subject}`}
          className="btn-secondary flex items-center space-x-2"
          target="_blank"
          rel="noopener noreferrer"
        >
          <EnvelopeIcon className="h-4 w-4" />
          <span>Open in Gmail</span>
        </a>
      </div>
    </div>
  )
}