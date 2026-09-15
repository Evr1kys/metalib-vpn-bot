import * as React from "react"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error' | 'info'
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variantStyles = {
      default: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
      secondary: 'bg-[#1a1a2e] text-gray-300 border border-[rgba(139,92,246,0.2)]',
      outline: 'text-gray-300 border border-[rgba(139,92,246,0.3)] bg-transparent',
      success: 'bg-[rgba(16,185,129,0.2)] text-emerald-400 border border-[rgba(16,185,129,0.3)]',
      warning: 'bg-[rgba(245,158,11,0.2)] text-amber-400 border border-[rgba(245,158,11,0.3)]',
      error: 'bg-[rgba(239,68,68,0.2)] text-red-400 border border-[rgba(239,68,68,0.3)]',
      info: 'bg-[rgba(59,130,246,0.2)] text-blue-400 border border-[rgba(59,130,246,0.3)]',
    }

    return (
      <div
        ref={ref}
        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold transition-colors ${variantStyles[variant]} ${className || ''}`}
        {...props}
      />
    )
  }
)
Badge.displayName = "Badge"

export { Badge }
