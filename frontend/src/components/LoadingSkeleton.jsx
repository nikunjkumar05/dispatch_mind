export default function LoadingSkeleton({ rows = 4, className = '' }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 bg-elevated rounded animate-pulse" 
             style={{ width: `${60 + Math.random() * 40}%` }} />
      ))}
    </div>
  )
}
