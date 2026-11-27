FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# Public, non-secret value baked into the client bundle (canonical URLs, sitemap).
ARG NEXT_PUBLIC_SITE_URL=http://localhost:8090
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Metadata and cached content may be prerendered while building the image.
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL
ARG RELEASE_REVISION
RUN RELEASE_REVISION="$RELEASE_REVISION" npm run build

FROM node:20-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
ARG RELEASE_REVISION
LABEL org.opencontainers.image.revision="$RELEASE_REVISION"
USER node
EXPOSE 3000
CMD ["node", "server.js"]
