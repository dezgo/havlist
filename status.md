# HavList — Project Status

## Deployment
- **Server:** Linux VPS (dgcloud), app at `/var/www/havlist`
- **Domain:** `havlist.appfoundry.cc` (HTTPS via Let's Encrypt)
- **Service:** systemd `havlist`, runs as user `derek`
- **Gunicorn:** unix socket at `/var/www/havlist/havlist.sock`, error log at `gunicorn-error.log`
- **Nginx:** reverse proxy to socket, `client_max_body_size 20M`
- **Auto-deploy:** GitHub Actions on push to `main`, runs `deploy.sh`
- **Sudoers:** derek can restart havlist service without password

## Features Implemented (2026-03-22)
- Multi-tenant auth (email/password, session-based)
- Item CRUD with all fields (name, description, category, brand, serial number, purchase info, warranty, location, condition, notes)
- Multi-photo upload with client-side compression (1920px max, JPEG 80%) + server-side Pillow fallback
- AI photo analysis via Claude API (Sonnet) — pre-fills form fields from photos
- PWA with network-first service worker, installable on iOS
- Fullscreen photo lightbox with tap navigation, arrows, swipe-down dismiss
- Location field with datalist (suggests existing values, allows new)
- Search and filter by category, location, free text
- Static asset cache busting via file mtime query params

## Known Issues / Notes
- Existing items from before multi-tenant have `user_id=0` — run `UPDATE items SET user_id=1 WHERE user_id=0` after first user registers to claim them
- iOS Safari edge-swipe-back cannot be prevented — lightbox uses tap zones + arrow buttons instead
- File inputs use `opacity:0` positioning instead of `hidden` attribute for mobile compatibility
