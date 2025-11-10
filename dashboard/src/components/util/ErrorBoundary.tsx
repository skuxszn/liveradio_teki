import * as React from 'react'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

type Props = { children: React.ReactNode }
type State = { hasError: boolean; error?: any }

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error }
  }

  componentDidCatch(error: any, info: any) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="max-w-md w-full space-y-4 text-center">
            <h1 className="text-2xl font-semibold">Something went wrong</h1>
            <p className="text-gray-600">Try reloading the page. If the problem persists, check Monitoring → Logs.</p>
            <div className="flex items-center justify-center gap-2">
              <Button onClick={() => window.location.reload()}>Reload</Button>
              <Link to="/monitoring"><Button variant="outline">View Logs</Button></Link>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}



