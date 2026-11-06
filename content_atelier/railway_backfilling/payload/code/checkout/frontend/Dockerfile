# syntax=docker/dockerfile:1

# Build context: content_atelier/frontend (not the workspace or backend).
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM node:24-alpine AS production
ENV NODE_ENV=production PORT=8080
WORKDIR /app
COPY server/package.json server/package-lock.json ./server/
RUN cd server && npm ci --omit=dev
COPY server ./server
COPY --from=build /app/dist ./dist
USER node
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider "http://127.0.0.1:${PORT}/health" || exit 1
CMD ["node", "server/index.mjs"]
