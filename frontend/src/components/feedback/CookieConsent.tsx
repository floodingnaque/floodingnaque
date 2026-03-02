/**
 * CookieConsent Component
 *
 * Displays a non-intrusive banner at the bottom of the viewport the
 * first time a user visits the application.  Once the user accepts or
 * declines, the preference is persisted in `localStorage` so the
 * banner is never shown again.
 *
 * Compliant with GDPR and the Philippine Data Privacy Act — no
 * non-essential cookies are set until the user gives consent.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Cookie, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const STORAGE_KEY = 'cookie-consent';

type ConsentValue = 'accepted' | 'declined';

/**
 * Renders a fixed-position cookie consent banner.
 * Automatically hidden once the user makes a choice.
 */
export function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Show the banner only when no preference has been stored
    const stored = localStorage.getItem(STORAGE_KEY) as ConsentValue | null;
    if (!stored) {
      setVisible(true);
    }
  }, []);

  function handleAccept() {
    localStorage.setItem(STORAGE_KEY, 'accepted' satisfies ConsentValue);
    setVisible(false);
  }

  function handleDecline() {
    localStorage.setItem(STORAGE_KEY, 'declined' satisfies ConsentValue);
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed inset-x-0 bottom-0 z-50 border-t bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80"
    >
      <div className="container mx-auto flex flex-col items-center gap-4 px-4 py-4 sm:flex-row sm:justify-between">
        {/* Message */}
        <div className="flex items-start gap-3 text-sm text-muted-foreground">
          <Cookie className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
          <p>
            We use essential cookies to keep the application running and optional
            analytics cookies to improve your experience.{' '}
            <Link to="/privacy" className="underline underline-offset-2 hover:text-foreground">
              Learn more
            </Link>
          </p>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 gap-2">
          <Button variant="outline" size="sm" onClick={handleDecline}>
            <X className="mr-1 h-4 w-4" aria-hidden="true" />
            Decline
          </Button>
          <Button size="sm" onClick={handleAccept}>
            Accept
          </Button>
        </div>
      </div>
    </div>
  );
}

export default CookieConsent;
