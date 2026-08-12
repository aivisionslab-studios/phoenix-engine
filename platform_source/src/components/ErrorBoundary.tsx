import { Component, ErrorInfo, ReactNode } from 'react';
import { RefreshCw, Trash2, ShieldAlert } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    (this as any).state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in Phoenix Aviary:', error, errorInfo);
    (this as any).setState({ errorInfo });
  }

  private handleResetState = () => {
    try {
      localStorage.removeItem('app_providers');
      localStorage.removeItem('app_parameters');
      localStorage.removeItem('app_conversations');
      localStorage.clear();
    } catch {
      // ignore
    }
    window.location.reload();
  };

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    const currentState = (this as any).state as State;
    const currentProps = (this as any).props as Props;

    if (currentState?.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
          <div className="max-w-xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
            
            <div className="flex items-center space-x-3 text-amber-400">
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                <ShieldAlert className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Phoenix Aviary Recovery</h1>
                <p className="text-xs text-slate-400">Recuperação Automática de Interface</p>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs font-mono space-y-2 text-rose-300 overflow-x-auto max-h-48">
              <p className="font-semibold text-rose-400">
                {currentState.error?.toString() || 'Erro inesperado na renderização.'}
              </p>
              {currentState.errorInfo?.componentStack && (
                <pre className="text-[10px] text-slate-500 whitespace-pre-wrap">
                  {currentState.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Detectamos uma exceção na interface. Você pode tentar recarregar a página ou restaurar os valores padrão dos provedores e conversas caso haja dados corrompidos no navegador.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
              <button
                onClick={this.handleReload}
                className="w-full sm:w-auto flex-1 flex items-center justify-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition-all shadow-md shadow-indigo-600/30"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Recarregar Página</span>
              </button>

              <button
                onClick={this.handleResetState}
                className="w-full sm:w-auto flex-1 flex items-center justify-center space-x-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-rose-300 hover:text-rose-200 border border-slate-700 font-semibold text-xs rounded-xl transition-all"
              >
                <Trash2 className="w-4 h-4" />
                <span>Restaurar Dados Padrão</span>
              </button>
            </div>

          </div>
        </div>
      );
    }

    return currentProps.children;
  }
}
