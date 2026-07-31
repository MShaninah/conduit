# syntax=docker/dockerfile:1

## ---- Stage 1: build the static Angular bundle ----
FROM node:20-alpine AS build

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

## ---- Stage 2: serve via Nginx ----
FROM nginx:1.27-alpine AS runtime

# Non-critical defaults configured directly in the image. FRONTEND_INTERNAL_PORT
# is the port Nginx listens on inside the container; BACKEND_HOST/BACKEND_PORT
# tell Nginx where to reverse-proxy /api requests (the backend Compose service).
ENV FRONTEND_INTERNAL_PORT=80 \
    BACKEND_HOST=backend \
    BACKEND_PORT=5000

COPY --from=build /build/dist/angular-conduit /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE ${FRONTEND_INTERNAL_PORT}

# The base nginx image's entrypoint renders /etc/nginx/templates/*.template
# into /etc/nginx/conf.d/*.conf via envsubst before launching nginx in the
# foreground - no custom entrypoint script needed, and nginx is not a dev
# server.
CMD ["nginx", "-g", "daemon off;"]
