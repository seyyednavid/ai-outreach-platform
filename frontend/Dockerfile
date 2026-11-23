# Frontend image in two stages:
#   1. build: Node turns the React code into plain HTML, CSS and JS
#   2. serve: nginx, a small web server, serves those files
# Only stage 2 ends up in the final image (no Node, no source code).

# ---- 1. build ---------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

# Dependencies first, reused until package-lock.json changes.
COPY package.json package-lock.json ./
RUN npm ci

# Vite reads frontend/.env here. It may only hold public VITE_ values
# (API address, Supabase URL, publishable key): they end up in the
# browser's JavaScript anyway. Never put a secret in frontend/.env.
COPY . .

# Production builds pass the same public values as build arguments:
#   docker build --build-arg VITE_API_BASE_URL=https://... ./frontend
# Build arguments become environment variables for "npm run build", and
# Vite prefers those over frontend/.env. Not passed (docker compose, CI):
# nothing is set, so frontend/.env is used exactly as before.
ARG VITE_API_BASE_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
RUN npm run build

# ---- 2. serve ---------------------------------------------------------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
