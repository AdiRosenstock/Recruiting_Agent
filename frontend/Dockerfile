# Multi-stage build producing the minimal `next build --output=standalone` runtime image (see
# next.config.ts and node_modules/next/dist/docs/01-app/01-getting-started/17-deploying.md).
#
# NEXT_PUBLIC_* variables are inlined into the client JS bundle at *build* time, not read at
# container startup -- so the backend URL the browser will call has to be a build arg, not a
# plain runtime env var. Pass it via `docker build --build-arg NEXT_PUBLIC_API_BASE_URL=...` or
# docker-compose's `build.args` (see ../docker-compose.yml).

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
