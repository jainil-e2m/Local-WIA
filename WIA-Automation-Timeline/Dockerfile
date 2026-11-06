# syntax=docker/dockerfile:1

# Single stage: the page is static and the server has no dependencies, so
# there is nothing to compile and nothing to npm-install. No build stage
# means no node_modules in the image at all.
FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app

COPY package.json ./
COPY server.mjs ./
COPY public ./public

# Railway assigns PORT at runtime; 8080 is the local/default fallback.
ENV PORT=8080
EXPOSE 8080

USER node

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["node", "server.mjs"]
