import { Box, Button, Skeleton } from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';

const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

/** Minimal shape of the Google Identity Services API this component uses. */
interface GoogleCredentialResponse {
  credential?: string;
}

interface GoogleAccountsId {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: {
      theme?: string;
      size?: string;
      width?: number;
      text?: string;
      shape?: string;
      logo_alignment?: string;
    },
  ) => void;
}

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleAccountsId } };
  }
}

let scriptPromise: Promise<void> | null = null;

/** Loads the GIS script once per page, no matter how many buttons mount. */
const loadGoogleScript = (): Promise<void> => {
  if (window.google?.accounts?.id) return Promise.resolve();
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('script failed')));
      return;
    }
    const script = document.createElement('script');
    script.src = GIS_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Google sign-in could not be loaded.'));
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    scriptPromise = null;
    throw error;
  });
  return scriptPromise;
};

interface GoogleSignInButtonProps {
  clientId: string;
  onCredential: (credential: string) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}

export const GoogleSignInButton = ({
  clientId,
  onCredential,
  onError,
  disabled = false,
}: GoogleSignInButtonProps): JSX.Element => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');

  // Kept in a ref so re-renders never re-initialise the Google client.
  const callbackRef = useRef(onCredential);
  callbackRef.current = onCredential;

  const handleCredential = useCallback(
    (response: GoogleCredentialResponse) => {
      if (response.credential) {
        callbackRef.current(response.credential);
      } else {
        onError('Google did not return a sign-in token. Please try again.');
      }
    },
    [onError],
  );

  useEffect(() => {
    let cancelled = false;

    void loadGoogleScript()
      .then(() => {
        if (cancelled) return;
        const identity = window.google?.accounts?.id;
        if (!identity || !containerRef.current) {
          setStatus('failed');
          return;
        }
        identity.initialize({
          client_id: clientId,
          callback: handleCredential,
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        containerRef.current.replaceChildren();
        identity.renderButton(containerRef.current, {
          theme: 'outline',
          size: 'large',
          width: 320,
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
        });
        setStatus('ready');
      })
      .catch(() => {
        if (!cancelled) setStatus('failed');
      });

    return () => {
      cancelled = true;
    };
  }, [clientId, handleCredential]);

  if (status === 'failed') {
    return (
      <Button variant="outlined" fullWidth disabled sx={{ borderColor: 'divider' }}>
        Google sign-in is unavailable
      </Button>
    );
  }

  return (
    <Box sx={{ position: 'relative', minHeight: 44 }}>
      {status === 'loading' && <Skeleton variant="rounded" height={44} />}
      <Box
        ref={containerRef}
        // The Google-rendered button cannot be styled, so it is centred and
        // dimmed rather than replaced while a sign-in is in flight.
        sx={{
          display: status === 'ready' ? 'flex' : 'none',
          justifyContent: 'center',
          opacity: disabled ? 0.5 : 1,
          pointerEvents: disabled ? 'none' : 'auto',
        }}
      />
    </Box>
  );
};
