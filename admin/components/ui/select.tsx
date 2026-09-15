import * as React from "react"
import { useState, useRef, useEffect } from "react"

export interface SelectProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  disabled?: boolean
  placeholder?: string
}

interface SelectContextType {
  value?: string
  onValueChange?: (value: string) => void
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  triggerRef: React.RefObject<HTMLButtonElement>
}

const SelectContext = React.createContext<SelectContextType | null>(null)

const Select = ({ children, value, onValueChange, disabled }: SelectProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  
  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (triggerRef.current && !triggerRef.current.parentElement?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])
  
  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false)
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen])
  
  return (
    <SelectContext.Provider value={{ value, onValueChange, isOpen, setIsOpen, triggerRef }}>
      <div className="relative">
        {children}
      </div>
    </SelectContext.Provider>
  )
}

const SelectTrigger = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }>(
  ({ className, children, ...props }, ref) => {
    const context = React.useContext(SelectContext)
    if (!context) throw new Error('SelectTrigger must be used within Select')
    
    return (
      <button
        ref={context.triggerRef}
        type="button"
        onClick={() => context.setIsOpen(!context.isOpen)}
        className={`flex h-11 w-full items-center justify-between rounded-xl border border-[rgba(139,92,246,0.2)] bg-[#1a1a2e] px-4 py-2 text-sm text-gray-300 ring-offset-[#0f0f1a] placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200 ${className || ''}`}
        {...props}
      >
        {children}
        <svg 
          className={`h-4 w-4 opacity-50 transition-transform ${context.isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    )
  }
)
SelectTrigger.displayName = "SelectTrigger"

const SelectValue = ({ placeholder }: { placeholder?: string }) => {
  const context = React.useContext(SelectContext)
  if (!context) throw new Error('SelectValue must be used within Select')
  
  return (
    <span className={context.value ? 'text-white' : 'text-gray-400'}>
      {context.value || placeholder}
    </span>
  )
}

const SelectContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const context = React.useContext(SelectContext)
    if (!context) throw new Error('SelectContent must be used within Select')
    
    if (!context.isOpen) return null
    
    return (
      <div
        ref={ref}
        className={`absolute z-50 mt-1 min-w-full overflow-hidden rounded-xl border border-[rgba(139,92,246,0.2)] bg-[#1a1a2e] text-gray-300 shadow-xl shadow-black/20 animate-in fade-in-0 zoom-in-95 ${className || ''}`}
        {...props}
      >
        <div className="p-1 max-h-60 overflow-auto">
          {children}
        </div>
      </div>
    )
  }
)
SelectContent.displayName = "SelectContent"

const SelectItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { value: string }>(
  ({ className, children, value, ...props }, ref) => {
    const context = React.useContext(SelectContext)
    if (!context) throw new Error('SelectItem must be used within Select')
    
    const isSelected = context.value === value
    
    return (
      <div
        ref={ref}
        onClick={() => {
          context.onValueChange?.(value)
          context.setIsOpen(false)
        }}
        className={`relative flex w-full cursor-pointer select-none items-center rounded-lg py-2.5 px-3 text-sm outline-none hover:bg-[rgba(139,92,246,0.1)] hover:text-white focus:bg-[rgba(139,92,246,0.1)] transition-colors ${isSelected ? 'bg-purple-500/20 text-white' : ''} ${className || ''}`}
        {...props}
      >
        {children}
        {isSelected && (
          <svg className="ml-auto h-4 w-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
    )
  }
)
SelectItem.displayName = "SelectItem"

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
