/**
 * Footer Component
 *
 * Dark footer with three columns: Brand, System Links, Credits.
 * Bottom bar with copyright notice.
 */

import { Droplets, Github, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

const SYSTEM_LINKS = [
  { label: 'Resident Dashboard', to: '/login' },
  { label: 'LGU Dashboard', to: '/login?role=lgu' },
  { label: 'Admin Portal', to: '/login?role=admin' },
] as const;

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer id="footer" className="bg-primary text-white/80 font-sans">
      <div className="container mx-auto px-4 py-14">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          {/* Column 1 — Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="h-9 w-9 rounded-full bg-white/15 flex items-center justify-center">
                <Droplets className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white tracking-tight leading-none">
                Floodingnaque
              </span>
            </div>
            <p className="text-sm leading-relaxed text-white/60 max-w-xs">
              Random Forest-based flood early warning system for Parañaque City
              using real-time weather data, tidal readings, and an interactive
              barangay-level dashboard.
            </p>
          </div>

          {/* Column 2 — System Links */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-white/40">
              System
            </h4>
            <ul className="space-y-2">
              {SYSTEM_LINKS.map((l) => (
                <li key={l.label}>
                  <Link
                    to={l.to}
                    className="text-sm text-white/60 hover:text-white transition-colors inline-flex items-center gap-1"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    {l.label}
                  </Link>
                </li>
              ))}
              <li>
                <a
                  href="https://github.com/KyaRhamil/floodingnaque"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-white/60 hover:text-white transition-colors inline-flex items-center gap-1"
                >
                  <Github className="h-3.5 w-3.5" />
                  Source Code
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3 — Credits */}
          <div className="space-y-4">
            <p className="text-sm text-white/60">
              Developed by Ramil &amp; Friends
            </p>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/10">
        <div className="container mx-auto px-4 py-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-white/40">
            &copy; {year} Floodingnaque
          </p>
          <p className="text-xs text-white/30">
            Built with React · Flask · Random Forest · Leaflet
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
