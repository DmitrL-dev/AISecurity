'use client'

import { useState, useEffect, createContext, useContext, useCallback, ReactNode } from 'react'
import { X, AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType>({
  toasts: [],
  addToast: () => {},
  removeToast: () => {},
})

export function useToast() {
  return useContext(ToastContext)
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const colorMap = {
  success: 'border-green-500 bg-green-500/10',
  error: 'border-red-500 bg-red-500/10',
  warning: 'border-yellow-500 bg-yellow-500/10',
  info: 'border-blue-500 bg-blue-500/10',
}

const iconColorMap = {
  success: 'text-green-400',
  error: 'text-red-400',
  warning: 'text-yellow-400',
  info: 'text-blue-400',
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: () => void }) {
  const Icon = iconMap[toast.type]

  useEffect(() => {
    const timer = setTimeout(onRemove, toast.duration || 5000)
    return () => clearTimeout(timer)
  }, [toast.duration, onRemove])

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm
        ${colorMap[toast.type]}
        animate-in slide-in-from-right-full duration-300
      `}
    >
      <Icon className={`w-5 h-5 flex-shrink-0 ${iconColorMap[toast.type]}`} />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-gray-400 mt-1">{toast.message}</p>
        )}
      </div>
      <button
        onClick={onRemove}
        className="p-1 hover:bg-white/10 rounded transition-colors"
      >
        <X className="w-4 h-4 text-gray-400" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts(prev => [...prev, { ...toast, id }])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      
      {/* Toast Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
        {toasts.map(toast => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onRemove={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  )
}
