import './steam-login.css';

interface SteamLoginProps {
  message?: string | undefined;
  onLogin?: (() => void) | undefined;
}

export default function SteamLogin({ message, onLogin }: SteamLoginProps) {
  return (
    <div className="steam-login">
      <p className="steam-login__notice">
        This app is not affiliated with Steam or Valve.
      </p>
      <p className="steam-login__notice">
        We use your Steam account identifier and publicly visible profile
        information to identify and display your player profile. Enter your
        Steam credentials only on Steam, never in this app.
      </p>
      {message && (
        <p className="steam-login__status" role="status">
          {message}
        </p>
      )}
      <button
        className="steam-login__button"
        onClick={onLogin ?? (() => window.location.assign('/api/v1/auth/steam/login'))}
        type="button"
      >
        <span className="steam-login__mark" aria-hidden="true">
          STEAM
        </span>
        Log in with Steam
      </button>
    </div>
  );
}
