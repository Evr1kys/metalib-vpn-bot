import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'link' | 'destructive'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const variantStyles = {
      default: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 shadow-lg shadow-purple-500/25',
      outline: 'border border-[rgba(139,92,246,0.3)] bg-transparent text-gray-300 hover:bg-[rgba(139,92,246,0.1)] hover:text-white hover:border-purple-500',
      secondary: 'bg-[#1a1a2e] text-gray-300 hover:bg-[#2a2a4a] hover:text-white border border-[rgba(139,92,246,0.2)]',
      ghost: 'text-gray-400 hover:bg-[rgba(139,92,246,0.1)] hover:text-white',
      link: 'text-purple-400 underline-offset-4 hover:underline hover:text-purple-300',
      destructive: 'bg-gradient-to-r from-red-500 to-rose-500 text-white hover:from-red-600 hover:to-rose-600 shadow-lg shadow-red-500/25',
    }

    const sizeStyles = {
      default: 'px-4 py-2.5',
      sm: 'px-3 py-1.5 text-xs',
      lg: 'px-6 py-3 text-base',
      icon: 'p-2 h-9 w-9',
    }

    return (
      <button
        className={`inline-flex items-center justify-center rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f1a] disabled:pointer-events-none disabled:opacity-50 ${sizeStyles[size]} ${variantStyles[variant]} ${className || ''}`}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
