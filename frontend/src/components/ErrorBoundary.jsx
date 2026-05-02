import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || 'Something went wrong.' }
  }

  componentDidCatch(error) {
    console.error('UI ERROR:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-100">
          <h2 className="font-bold">View failed safely</h2>
          <p className="mt-2 text-sm">{this.state.message}</p>
        </section>
      )
    }

    return this.props.children
  }
}
