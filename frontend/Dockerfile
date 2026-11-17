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
RUN npm run build

# ---- 2. serve ---------------------------------------------------------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
