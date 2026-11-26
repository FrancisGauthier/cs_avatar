import { isSafeSteamAvatarUrl, type SteamSession } from './types';
import './steam-profile.css';

interface SteamProfileProps {
  profile: SteamSession;
}

export default function SteamProfile({ profile }: SteamProfileProps) {
  const displayName = profile.personaName ?? 'Steam player';
  const avatarUrl = isSafeSteamAvatarUrl(profile.avatarUrl) ? profile.avatarUrl : null;

  return (
    <section className="steam-profile" aria-label="Signed-in Steam profile">
      {avatarUrl ? (
        <img
          className="steam-profile__avatar"
          src={avatarUrl}
          alt={`${displayName}'s Steam profile picture`}
          referrerPolicy="no-referrer"
        />
      ) : (
        <span
          className="steam-profile__fallback"
          role="img"
          aria-label="Profile picture unavailable"
        >
          ?
        </span>
      )}
      <div className="steam-profile__details">
        <p className="steam-profile__label">Signed in with Steam</p>
        <h2>{displayName}</h2>
        {profile.profileStatus === 'UNAVAILABLE' && (
          <p className="steam-profile__status" role="status">
            Your Steam account is signed in, but public profile details are
            unavailable.
          </p>
        )}
      </div>
    </section>
  );
}
