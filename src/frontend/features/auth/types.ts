export type ProfileStatus = 'AVAILABLE' | 'UNAVAILABLE';

export interface SteamSession {
  steamId: string;
  personaName: string | null;
  avatarUrl: string | null;
  profileStatus: ProfileStatus;
}

const steamAvatarHosts = new Set([
  'avatars.akamai.steamstatic.com',
  'avatars.steamstatic.com',
  'cdn.akamai.steamstatic.com',
  'steamcdn-a.akamaihd.net',
]);

export function isSafeSteamAvatarUrl(value: string | null): value is string {
  if (!value || value.length > 2048) {
    return false;
  }

  try {
    const url = new URL(value);
    return (
      url.protocol === 'https:' &&
      steamAvatarHosts.has(url.hostname.toLowerCase()) &&
      (url.port === '' || url.port === '443') &&
      url.username === '' &&
      url.password === '' &&
      url.pathname.startsWith('/') &&
      url.hash === ''
    );
  } catch {
    return false;
  }
}

export function parseSteamSession(value: unknown): SteamSession {
  if (
    typeof value !== 'object' ||
    value === null ||
    !('steamId' in value) ||
    !('personaName' in value) ||
    !('avatarUrl' in value) ||
    !('profileStatus' in value)
  ) {
    throw new Error('The session response is malformed');
  }

  const session = value as Record<string, unknown>;
  if (
    typeof session.steamId !== 'string' ||
    !/^[0-9]{17}$/.test(session.steamId) ||
    (session.personaName !== null &&
      (typeof session.personaName !== 'string' ||
        session.personaName.length === 0 ||
        session.personaName.length > 128)) ||
    (session.avatarUrl !== null && typeof session.avatarUrl !== 'string') ||
    (session.profileStatus !== 'AVAILABLE' && session.profileStatus !== 'UNAVAILABLE')
  ) {
    throw new Error('The session response is malformed');
  }

  if (session.profileStatus === 'AVAILABLE' && session.personaName === null) {
    throw new Error('The session response is missing its player nickname');
  }

  return {
    steamId: session.steamId,
    personaName: session.personaName,
    avatarUrl: isSafeSteamAvatarUrl(session.avatarUrl as string | null)
      ? session.avatarUrl
      : null,
    profileStatus: session.profileStatus,
  };
}
