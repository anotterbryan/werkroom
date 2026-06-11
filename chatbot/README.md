# Werkroom Librarian — OPTIONAL Cloudflare Worker (currently unused)

> **Status (2026-06-11): not deployed, not needed.** The site's "Ask the
> Library" runs **fully in-browser** — a deterministic intent engine over the
> database plus keyword search of `site/kb/facts.json`. No accounts, no API
> keys. This folder is kept only in case a generative upgrade is ever wanted.

# Original deploy guide (≈5 minutes)

The chatbot is a Cloudflare Worker that holds your Anthropic API key, retrieves
facts from the site's knowledge pack (`site/kb/facts.json`, rebuilt by
`scripts/build_knowledge_pack.py`), and answers grounded questions with Claude.
The static site never sees the key.

## One-time setup (on your Mac)

1. **Anthropic API key** — create one at https://console.anthropic.com →
   API Keys. (Usage is pay-as-you-go; the worker uses Claude Haiku, so a chat
   answer costs a fraction of a cent.)
2. **Cloudflare account** — free tier at https://dash.cloudflare.com/sign-up.
3. In Terminal:

   ```bash
   cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Art/Werkroom/files/rpdr-tracking/chatbot
   npx wrangler login                       # opens browser, authorize
   npx wrangler secret put ANTHROPIC_API_KEY   # paste the key when prompted
   npx wrangler deploy
   ```

   The deploy prints your worker URL, e.g.
   `https://werkroom-librarian.<your-subdomain>.workers.dev`

4. **Connect the site**: in `site/index.html`, find
   `const CHAT_ENDPOINT = ''` and set it to the worker URL. Commit + push.

## Updating the knowledge

After any data change: `python scripts/build_knowledge_pack.py` (alongside
`build_site_data.py`), commit, push. The worker caches the pack for 1 hour.

## Notes

- CORS allows only the GitHub Pages origin (edit `ALLOW_ORIGINS` in worker.js
  if the site moves).
- The model answers ONLY from retrieved facts and returns site routes the chat
  view renders as "explore →" links.
- Free Cloudflare tier: 100k requests/day — far more than this needs.
