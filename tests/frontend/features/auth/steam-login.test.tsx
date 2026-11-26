import { fireEvent, render, screen } from '@testing-library/react';

import SteamLogin from '../../../../src/frontend/features/auth/SteamLogin';
import SteamProfile from '../../../../src/frontend/features/auth/SteamProfile';
import type { SteamSession } from '../../../../src/frontend/features/auth/types';

const profile: SteamSession = {
  steamId: '76561198000000000',
  personaName: 'Example Player',
  avatarUrl: 'https://steamcdn-a.akamaihd.net/example.jpg',
  profileStatus: 'AVAILABLE',
};

describe('Steam login and profile components', () => {
  it('explains provider affiliation and profile data use before sign-in', () => {
    const onLogin = vi.fn();
    render(<SteamLogin onLogin={onLogin} />);

    expect(screen.getByRole('button', { name: 'Log in with Steam' })).toBeVisible();
    expect(screen.getByText(/not affiliated with Steam or Valve/i)).toBeVisible();
    expect(screen.getByText(/account identifier and publicly visible profile information/i)).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Steam' }));
    expect(onLogin).toHaveBeenCalledOnce();
  });

  it('shows a clear retryable message after cancellation or failure', () => {
    render(<SteamLogin message="Steam sign-in did not complete. Please try again." />);

    expect(screen.getByRole('status')).toHaveTextContent(
      'Steam sign-in did not complete. Please try again.',
    );
    expect(screen.getByRole('button', { name: 'Log in with Steam' })).toBeEnabled();
  });

  it('renders the authenticated nickname and safe profile picture', () => {
    render(<SteamProfile profile={profile} />);

    expect(screen.getByText('Example Player')).toBeVisible();
    expect(screen.getByRole('img', { name: "Example Player's Steam profile picture" })).toHaveAttribute(
      'src',
      profile.avatarUrl,
    );
  });

  it('uses a neutral fallback when the profile image is unavailable', () => {
    render(
      <SteamProfile
        profile={{
          ...profile,
          avatarUrl: null,
          profileStatus: 'UNAVAILABLE',
        }}
      />,
    );

    expect(screen.getByText('Example Player')).toBeVisible();
    expect(screen.getByRole('img', { name: 'Profile picture unavailable' })).toBeVisible();
  });
});
