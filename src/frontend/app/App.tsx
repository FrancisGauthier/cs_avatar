import { useEffect, useRef, useState } from 'react';

import {
  beginSteamLogin,
  endCurrentSession,
  getCurrentSession,
} from '../features/auth/api';
import SteamLogin from '../features/auth/SteamLogin';
import SteamProfile from '../features/auth/SteamProfile';
import type { SteamSession } from '../features/auth/types';

type SessionState = 'loading' | 'signed-out' | 'signed-in' | 'error';

function isSignedOutMessage(data: unknown): boolean {
  return (
    typeof data === 'object' &&
    data !== null &&
    'type' in data &&
    data.type === 'signed-out'
  );
}

export default function App() {
  const [session, setSession] = useState<SteamSession | null>(null);
  const [state, setState] = useState<SessionState>('loading');
  const [message, setMessage] = useState<string>();
  const [signOutError, setSignOutError] = useState<string>();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const signOutChannel = useRef<BroadcastChannel | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('steam_login') === 'failed') {
      setMessage('Steam sign-in did not complete. Please try again.');
      window.history.replaceState(null, '', window.location.pathname);
    }

    let active = true;
    const channel =
      typeof BroadcastChannel === 'undefined'
        ? null
        : new BroadcastChannel('cs-avatar-auth');
    signOutChannel.current = channel;

    const showSignedOut = () => {
      setSession(null);
      setState('signed-out');
      setMessage(undefined);
      setSignOutError(undefined);
      setIsSigningOut(false);
    };

    const refreshSession = async () => {
      try {
        const currentSession = await getCurrentSession();
        if (!active) {
          return;
        }
        setSession(currentSession);
        setState(currentSession ? 'signed-in' : 'signed-out');
        if (!currentSession) {
          setSignOutError(undefined);
        }
      } catch {
        if (!active) {
          return;
        }
        setMessage('We could not check your Steam session. You can try signing in again.');
        setState((currentState) => (currentState === 'signed-in' ? 'signed-in' : 'error'));
      }
    };

    if (channel) {
      channel.onmessage = (event: MessageEvent<unknown>) => {
        if (isSignedOutMessage(event.data)) {
          showSignedOut();
        }
      };
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void refreshSession();
      }
    };

    window.addEventListener('pageshow', refreshSession);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    void refreshSession();

    return () => {
      active = false;
      window.removeEventListener('pageshow', refreshSession);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (channel) {
        channel.onmessage = null;
        channel.close();
        signOutChannel.current = null;
      }
    };
  }, []);

  const handleSignOut = async () => {
    setIsSigningOut(true);
    setSignOutError(undefined);
    try {
      await endCurrentSession();
      setSession(null);
      setState('signed-out');
      setMessage(undefined);
      setSignOutError(undefined);
      signOutChannel.current?.postMessage({ type: 'signed-out' });
    } catch {
      setSignOutError('We could not sign out. Please try again.');
    } finally {
      setIsSigningOut(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <p className="app-kicker">CS AVATAR</p>
        <h1>{state === 'signed-in' ? 'Your player profile' : 'Welcome'}</h1>
      </header>
      <section className="auth-panel" aria-labelledby="auth-heading">
        <h2 id="auth-heading">
          {state === 'signed-in' ? 'Your account' : 'Sign in to continue'}
        </h2>
        {state === 'loading' && <p role="status">Checking your Steam session…</p>}
        {state === 'signed-in' && session && (
          <SteamProfile
            profile={session}
            signOutError={signOutError}
            isSigningOut={isSigningOut}
            onSignOut={handleSignOut}
          />
        )}
        {(state === 'signed-out' || state === 'error') && (
          <SteamLogin message={message} onLogin={beginSteamLogin} />
        )}
      </section>
    </main>
  );
}
