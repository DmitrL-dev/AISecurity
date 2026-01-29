'use client'

interface SkeletonProps {
  className?: string
  style?: React.CSSProperties
}

export function Skeleton({ className = '', style }: SkeletonProps) {
  return (
    <div 
      className={`animate-pulse bg-gradient-to-r from-[#1a1f2e] via-[#242938] to-[#1a1f2e] bg-[length:200%_100%] rounded ${className}`}
      style={{ animation: 'shimmer 1.5s infinite', ...style }}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
      <div className="flex justify-between items-start mb-4">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-6 w-16" />
        </div>
        <Skeleton className="w-10 h-10 rounded-lg" />
      </div>
      <div className="flex gap-1 h-8">
        {[...Array(10)].map((_, i) => (
          <Skeleton key={i} className="flex-1 rounded-t" style={{ height: `${30 + Math.random() * 60}%` }} />
        ))}
      </div>
    </div>
  )
}

export function TableRowSkeleton() {
  return (
    <tr className="border-b border-[#374151]/50">
      <td className="p-4">
        <div className="space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-4 w-48" />
        </div>
      </td>
      <td className="p-4"><Skeleton className="h-5 w-16 rounded" /></td>
      <td className="p-4"><Skeleton className="h-4 w-20" /></td>
      <td className="p-4"><Skeleton className="h-4 w-16" /></td>
      <td className="p-4"><Skeleton className="h-4 w-16" /></td>
      <td className="p-4"><Skeleton className="h-4 w-20" /></td>
    </tr>
  )
}

export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
      <Skeleton className="h-5 w-32 mb-4" />
      <Skeleton className="w-full" style={{ height }} />
    </div>
  )
}
