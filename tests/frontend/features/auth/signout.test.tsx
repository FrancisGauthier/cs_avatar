import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

import App from '../../../../src/frontend/app/App';
import type { SteamSession } from '../../../../src/frontend/features/auth/types';

const profile: SteamSession = {
  steamId: '76561198000000000',
  personaName: 'Example Player',
  avatarUrl: 'https://steamcdn-a.akamaihd.net/example.jpg',
  profileStatus: 'AVAILABLE',
};

class TestBroadcastChannel {
  static instances: TestBroadcastChannel[] = [];

  onmessage: ((event: MessageEvent) => void) | null = null;
  postMessage = vi.fn();
  close = vi.fn();

  constructor(readonly name: string) {
    TestBroadcastChannel.instances.push(this);
  }

  receive(data: unknown): void {
    this.onmessage?.({ data } as MessageEvent);
  }
}

function sessionResponse(session: SteamSession | null, status = 200): Response {
  return new Response(session ? JSON.stringify(session) : null, {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Steam app sign-out', () => {
  beforeEach(() => {
    TestBroadcastChannel.instances = [];
    vi.stubGlobal('BroadcastChannel', TestBroadcastChannel);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('ends the app session and broadcasts sign-out after server confirmation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sessionResponse(profile))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);

    expect(await screen.findByText('Example Player')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Log in with Steam' })).toBeVisible();
    });
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeVisible();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/logout',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
      }),
    );
    expect(TestBroadcastChannel.instances[0]?.postMessage).toHaveBeenCalledWith({
      type: 'signed-out',
    });
    expect(screen.queryByText('Example Player')).not.toBeInTheDocument();
  });

  it('keeps the profile visible and reports failure when sign-out is not confirmed', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sessionResponse(profile))
      .mockResolvedValueOnce(new Response(null, { status: 503 }));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);

    expect(await screen.findByText('Example Player')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(
      await screen.findByText(/could not sign out/i),
    ).toBeVisible();
    expect(screen.getByText('Example Player')).toBeVisible();
    expect(TestBroadcastChannel.instances[0]?.postMessage).not.toHaveBeenCalled();
  });

  it('clears stale profile state when another app tab signs out', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(sessionResponse(profile)),
    );
    render(<App />);

    expect(await screen.findByText('Example Player')).toBeVisible();
    act(() => {
      TestBroadcastChannel.instances[0]?.receive({ type: 'signed-out' });
    });

    expect(screen.getByRole('button', { name: 'Log in with Steam' })).toBeVisible();
    expect(screen.queryByText('Example Player')).not.toBeInTheDocument();
  });

  it('rechecks the session when a page is restored', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sessionResponse(profile))
      .mockResolvedValueOnce(sessionResponse(null, 401));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);

    expect(await screen.findByText('Example Player')).toBeVisible();
    window.dispatchEvent(new PageTransitionEvent('pageshow'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Log in with Steam' })).toBeVisible();
    });
    expect(screen.queryByText('Example Player')).not.toBeInTheDocument();
  });
});
