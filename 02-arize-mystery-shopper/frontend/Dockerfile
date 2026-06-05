# Self-Improving QA Agent — frontend image.
#
# Standard Next.js standalone build. Outputs to /app/.next/standalone with
# the server.js entrypoint Cloud Run expects.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.jso[n] ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public 2>/dev/null || true
EXPOSE 3000
CMD ["node", "server.js"]
