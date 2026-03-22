# HavList

Personal inventory management PWA — Python/Flask, SQLite, mobile-first.

## Key Info
- **Repo:** github.com/dezgo/havlist (SSH alias: `github-personal`)
- **Domain:** `havlist.appfoundry.cc`
- **Server path:** `/var/www/havlist` (NOT `/opt/havlist`)
- **Auto-deploy:** GitHub Actions on push to `main` via `deploy.sh`

## Dev Notes
- iPhone is the primary test device
- PWA caching has caused issues — service worker is network-first, static assets use `?v=<mtime>` cache busting
- iOS Safari: edge-swipe-back can't be prevented; `hidden` on file inputs breaks on mobile — use `opacity:0` positioning
- Client-side image compression happens in browser before upload

## References
- See [status.md](status.md) for full deployment details, feature list, and known issues
- See [deploy.md](deploy.md) for VPS setup instructions
