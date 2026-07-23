# figgydeck landing page

A static, dependency-free landing page for figgydeck. Two files, no build step:

- `index.html` — the page.
- `styles.css` — the "Organic" design-system stylesheet (tokens + component
  classes) the page is built from. Fonts (Caprasimo + Figtree) load from Google
  Fonts via an `@import` at the top.

It was designed in [Claude Design](https://claude.ai/design) and exported here
with the design-canvas runtime stripped out, so it's plain HTML/CSS.

## Preview locally

```bash
python -m http.server -d site 8000
# then open http://localhost:8000
```

## Deploy — Cloudflare Pages

Deploys are automated by `.github/workflows/deploy-site.yml`:

- push to `main` touching `site/**` → **production** deploy
- any pull request touching `site/**` → **preview** deploy on a per-PR URL

Production is served at **https://figgydeck.gregjoeval.com** (with
`figgydeck.pages.dev` as the underlying Pages URL).

### One-time Cloudflare setup

These steps happen once, outside the repo (a free Cloudflare account is enough):

1. **Create the Pages project** named `figgydeck`, production branch `main`.
   Either in the dashboard (Workers & Pages → Create → Pages → *Direct Upload*,
   name it `figgydeck`), or from a terminal:
   ```bash
   npx wrangler login
   npx wrangler pages project create figgydeck --production-branch=main
   ```
2. **Create an API token** with the *Cloudflare Pages → Edit* permission
   (My Profile → API Tokens → Create Token → "Cloudflare Pages" template).
3. **Find your Account ID** (any domain's overview page, or `npx wrangler whoami`).
4. **Add two GitHub repo secrets** (Settings → Secrets and variables → Actions):
   - `CLOUDFLARE_API_TOKEN` — the token from step 2
   - `CLOUDFLARE_ACCOUNT_ID` — the ID from step 3

   Or via the CLI:
   ```bash
   gh secret set CLOUDFLARE_API_TOKEN
   gh secret set CLOUDFLARE_ACCOUNT_ID
   ```

After that, every push/PR deploys automatically.

### Attach the custom domain (one-time)

Once the project has a production deployment, in the Cloudflare dashboard go to
**Workers & Pages → figgydeck → Custom domains → Set up a custom domain** and
enter `figgydeck.gregjoeval.com`. Because the `gregjoeval.com` zone is in the
same Cloudflare account, the CNAME is created and validated automatically — no
manual DNS edit needed.

Any static host works too (GitHub Pages, Netlify, Vercel) — just serve this
`site/` directory.
