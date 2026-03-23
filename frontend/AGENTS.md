# Scope
- Applies to `frontend/` Next.js app routes, components, styles, and browser-side config.

# Read First
- `frontend/package.json`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx` or the touched route
- `frontend/lib/config.ts` and the touched component file

# Local Rules
- Preserve existing App Router and TypeScript patterns.
- Keep client/server boundaries explicit.
- Reuse existing components and `lib/` helpers before adding files.
- Keep Tailwind and CSS changes local; change `app/globals.css` only for shared behavior.
- Update `frontend/.env.example` if frontend env requirements change.

# Definition Of Done
- UI behavior works in the touched flow on desktop and mobile.
- Relevant frontend checks pass, or gaps and risks are stated explicitly.
