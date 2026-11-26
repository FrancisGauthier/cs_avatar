import { useEffect, useState } from 'react';

import { beginSteamLogin, getCurrentSession } from '../features/auth/api';
import SteamLogin from '../features/auth/SteamLogin';
import SteamProfile from '../features/auth/SteamProfile';
import type { SteamSession } from '../features/auth/types';

type SessionState = 'loading' | 'signed-out' | 'signed-in' | 'error';

export default function App() {
  const [session, setSession] = useState<SteamSession | null>(null);
  const [state, setState] = useState<SessionState>('loading');
  const [message, setMessage] = useState<string>();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('steam_login') === 'failed') {
      setMessage('Steam sign-in did not complete. Please try again.');
      window.history.replaceState(null, '', window.location.pathname);
    }

    let active = true;
    getCurrentSession()
      .then((currentSession) => {
        if (!active) {
          return;
        }
        setSession(currentSession);
        setState(currentSession ? 'signed-in' : 'signed-out');
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setMessage('We could not check your Steam session. You can try signing in again.');
        setState('error');
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app-shell">
      <header className="app-header">
        <p className="app-kicker">CS AVATAR</p>
        <h1>Your player profile</h1>
      </header>
      <section className="auth-panel" aria-labelledby="auth-heading">
        <h2 id="auth-heading">
          {state === 'signed-in' ? 'Your account' : 'Sign in to continue'}
        </h2>
        {state === 'loading' && <p role="status">Checking your Steam session…</p>}
        {state === 'signed-in' && session && <SteamProfile profile={session} />}
        {(state === 'signed-out' || state === 'error') && (
          <SteamLogin message={message} onLogin={beginSteamLogin} />
        )}
      </section>
    </main>
  );
}
