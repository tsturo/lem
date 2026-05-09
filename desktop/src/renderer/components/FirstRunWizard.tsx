import { BrandMark } from './BrandMark'

export type WizardVariant = 'not-found' | 'auth-expired'

interface FirstRunWizardProps {
  variant: WizardVariant
  claudePath?: string
  onRetry: () => void
}

export function FirstRunWizard({ variant, claudePath, onRetry }: FirstRunWizardProps) {
  async function handleInstall() {
    await window.lem.shell.openExternal('https://claude.com/claude-code')
  }

  async function handlePickPath() {
    const picked = await window.lem.claude.pickPath()
    if (picked) {
      const current = await window.lem.settings.get()
      await window.lem.settings.set({ ...current, claudePath: picked })
      onRetry()
    }
  }

  async function handleLogin() {
    const path = claudePath
    if (path) await window.lem.claude.login(path)
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: 'var(--t-bg)',
    }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        padding: '48px 40px',
        background: 'var(--t-card-bg)',
        borderRadius: 'var(--t-radius-xl)',
        border: '1px solid var(--t-border)',
        boxShadow: 'var(--t-shadow-card)',
        maxWidth: '440px',
        width: '100%',
      }}>
        <div style={{ marginBottom: '20px' }}>
          <BrandMark size={42} />
        </div>

        {variant === 'not-found' ? (
          <>
            <h1 style={{
              margin: '0 0 12px',
              fontSize: '28px',
              fontWeight: 700,
              color: 'var(--t-text)',
              lineHeight: 1.2,
            }}>
              lem needs Claude Code
            </h1>
            <p style={{
              margin: '0 0 32px',
              fontSize: '15px',
              lineHeight: 1.6,
              color: 'var(--t-text-2)',
            }}>
              lem uses your local Claude Code installation to run AI agents.
              We couldn't find it on your machine.
            </p>
            <button
              onClick={handleInstall}
              style={{
                width: '100%',
                padding: '12px 24px',
                marginBottom: '12px',
                fontSize: '15px',
                fontWeight: 600,
                color: '#ffffff',
                background: 'var(--t-grad)',
                border: 'none',
                borderRadius: 'var(--t-radius-pill)',
                cursor: 'pointer',
                boxShadow: 'var(--t-shadow-cta)',
              }}
            >
              Install Claude Code
            </button>
            <button
              onClick={onRetry}
              style={{
                width: '100%',
                padding: '10px 24px',
                marginBottom: '16px',
                fontSize: '14px',
                fontWeight: 500,
                color: 'var(--t-text)',
                background: 'var(--t-surface)',
                border: '1px solid var(--t-border)',
                borderRadius: 'var(--t-radius-pill)',
                cursor: 'pointer',
              }}
            >
              I've installed it — retry detection
            </button>
            <button
              onClick={handlePickPath}
              style={{
                background: 'none',
                border: 'none',
                padding: '4px 8px',
                fontSize: '13px',
                color: 'var(--t-text-3)',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Set custom path…
            </button>
          </>
        ) : (
          <>
            <h1 style={{
              margin: '0 0 12px',
              fontSize: '28px',
              fontWeight: 700,
              color: 'var(--t-text)',
              lineHeight: 1.2,
            }}>
              Sign in to Claude
            </h1>
            <p style={{
              margin: '0 0 32px',
              fontSize: '15px',
              lineHeight: 1.6,
              color: 'var(--t-text-2)',
            }}>
              Your Claude session has expired. Click below to sign in again.
            </p>
            <button
              onClick={handleLogin}
              style={{
                width: '100%',
                padding: '12px 24px',
                marginBottom: '12px',
                fontSize: '15px',
                fontWeight: 600,
                color: '#ffffff',
                background: 'var(--t-grad)',
                border: 'none',
                borderRadius: 'var(--t-radius-pill)',
                cursor: 'pointer',
                boxShadow: 'var(--t-shadow-cta)',
              }}
            >
              Sign in to Claude
            </button>
            <button
              onClick={onRetry}
              style={{
                width: '100%',
                padding: '10px 24px',
                fontSize: '14px',
                fontWeight: 500,
                color: 'var(--t-text)',
                background: 'var(--t-surface)',
                border: '1px solid var(--t-border)',
                borderRadius: 'var(--t-radius-pill)',
                cursor: 'pointer',
              }}
            >
              Retry
            </button>
          </>
        )}
      </div>
    </div>
  )
}
