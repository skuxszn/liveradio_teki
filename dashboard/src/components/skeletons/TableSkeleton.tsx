export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="rounded-lg border bg-white shadow-sm p-0">
      <div className="border-b p-4 bg-gray-50 animate-pulse h-10" />
      <div className="divide-y">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4 p-4">
            <div className="h-4 w-6 bg-gray-200 rounded" />
            <div className="h-4 flex-1 bg-gray-200 rounded" />
            <div className="h-4 w-24 bg-gray-200 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}



