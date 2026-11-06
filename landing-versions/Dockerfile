# syntax=docker/dockerfile:1

# ---- Build stage ---------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app

# Install deps first so this layer only invalidates on lockfile changes
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Public Content Atelier destination for the landing page.
ARG VITE_CONTENT_ATELIER_URL=""
ENV VITE_CONTENT_ATELIER_URL=$VITE_CONTENT_ATELIER_URL

# No audit-service URL is built into the bundle: every audit product is called
# through the Express BFF at runtime, so their URLs and bearer tokens never
# enter the browser bundle. Public destinations and enable flags are build-time values.

# Per-automation enable flags (see src/data/toolFlags.ts). These are VITE_
# variables, so they are compiled into the bundle here rather than read at
# runtime — Railway exposes service variables as build args, but a variable
# with no ARG declared is silently dropped, which would leave a tile stuck on
# whatever status is committed in data/tools.ts. Blank means "no opinion": the
# committed status wins, so an unset flag never changes behaviour.
ARG VITE_TOOL_TECHNICAL_SEO_ENABLED=""
ARG VITE_TOOL_AI_SEO_ENABLED=""
ARG VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED=""
ARG VITE_TOOL_ON_PAGE_SEO_ENABLED=""
ARG VITE_TOOL_LEAD_MAGNET_ENABLED=""
ENV VITE_TOOL_TECHNICAL_SEO_ENABLED=$VITE_TOOL_TECHNICAL_SEO_ENABLED \
    VITE_TOOL_AI_SEO_ENABLED=$VITE_TOOL_AI_SEO_ENABLED \
    VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED=$VITE_TOOL_AI_PRESENCE_CHECKER_ENABLED \
    VITE_TOOL_ON_PAGE_SEO_ENABLED=$VITE_TOOL_ON_PAGE_SEO_ENABLED \
    VITE_TOOL_LEAD_MAGNET_ENABLED=$VITE_TOOL_LEAD_MAGNET_ENABLED

# DEV/DEMO AUTH BYPASS — the client half of it.
#
# Declared here for the same reason as the flags above: Railway exposes service
# variables as build args, and one with no ARG is SILENTLY DROPPED. Without
# this line, setting VITE_AUTH_DISABLED=1 on the service would appear to work,
# change nothing, and leave the React route guard (src/components/RequireAuth
# .tsx) still redirecting to /login while the API sat wide open — the most
# confusing of the possible half-states.
#
# Defaults to "" so an unset variable keeps real auth. It is a BUILD ARG, so
# turning it on or off needs a REDEPLOY, not a restart — unlike its server-side
# twin AUTH_DISABLED, which is a runtime variable.
#
# Both are needed together. Bypassing only the guard leaves every fetch 401ing;
# bypassing only the API still shows a login screen (which any password opens).
ARG VITE_AUTH_DISABLED=""
ENV VITE_AUTH_DISABLED=$VITE_AUTH_DISABLED

RUN npm run build

# ---- Production stage ------------------------------------------------------
# Node runtime (replacing the earlier nginx stage): the Express server in
# server/ both serves the built SPA and handles the /api/auth/* session
# endpoints. Runs as the non-root `node` user.
FROM node:24-alpine AS production
ENV NODE_ENV=production
WORKDIR /app

COPY server/package.json server/package-lock.json ./server/
RUN cd server && npm ci --omit=dev

COPY server ./server
COPY --from=build /app/dist ./dist

# Railway assigns PORT at runtime; 8080 is the local/default fallback.
ENV PORT=8080
EXPOSE 8080

USER node

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["node", "server/index.mjs"]
