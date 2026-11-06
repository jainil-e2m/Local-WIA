import React from 'react';
import { ErrorState } from './states';

/* An error boundary around each view (plan 1.F2): a render error in one view shows a message in that view's place and
   leaves the rest of the app working. The boundary clears itself when the person navigates (`resetKey`) or retries. */

interface Props { name: string; resetKey?: string; children: React.ReactNode }
interface State { failed: Error | null; key: string | undefined }

export class ViewBoundary extends React.Component<Props, State> {
  state: State = { failed: null, key: this.props.resetKey };

  static getDerivedStateFromError(error: Error): Partial<State> { return { failed: error }; }

  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    return props.resetKey !== state.key ? { failed: null, key: props.resetKey } : null;
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`The ${this.props.name} screen failed to render.`, error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return <section data-view-failed={this.props.name} className="py-6 max-w-3xl mx-auto space-y-3">
      <h1 className="font-editorial text-2xl text-[#173354]">This screen hit a problem</h1>
      <ErrorState message={`${this.props.name} could not be shown. The rest of Content Atelier still works; your saved work is not affected.`}
        onRetry={() => this.setState({ failed: null })} retryLabel="Try again" />
    </section>;
  }
}
