import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryState {
  error: Error | null;
}

/** Последний рубеж: вместо белого экрана показываем понятное сообщение и кнопку перезагрузки. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('MAX Спот: необработанная ошибка интерфейса', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="card max-w-sm text-center shadow-float">
          <p className="text-4xl" aria-hidden>
            🏀
          </p>
          <h1 className="mt-3 text-lg font-bold">Что-то пошло не так</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Мы уже знаем об ошибке. Перезагрузите мини-приложение, данные не потеряются.
          </p>
          <button type="button" className="btn-primary mt-4 w-full" onClick={() => window.location.reload()}>
            Перезагрузить
          </button>
        </div>
      </div>
    );
  }
}
