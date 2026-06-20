import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-signal-red/10 border border-signal-red/20 rounded-xl p-6 text-center max-w-md">
        <AlertTriangle className="w-10 h-10 text-signal-red mx-auto mb-3" />
        <p className="text-chalk font-medium mb-1">Failed to load data</p>
        <p className="text-muted text-sm mb-4">{message}</p>
        {onRetry && (
          <button onClick={onRetry}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent rounded-lg hover:bg-accent/20 transition-colors text-sm font-medium">
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
