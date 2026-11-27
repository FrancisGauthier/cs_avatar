import { parseSteamSession, type SteamSession } from './types';

export async function getCurrentSession(): Promise<SteamSession | null> {
  const response = await fetch('/api/v1/auth/session', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });

  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error('Could not load the Steam session');
  }

  return parseSteamSession(await response.json());
}

export async function endCurrentSession(): Promise<void> {
  const response = await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });

  if (response.status !== 204) {
    throw new Error('Could not sign out of the Steam session');
  }
}

export function beginSteamLogin(): void {
  window.location.assign('/api/v1/auth/steam/login');
}
