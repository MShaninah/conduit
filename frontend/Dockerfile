## ---- Stage 1: build the static Angular bundle ----
FROM node:20-alpine AS build

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

## ---- Stage 2: serve via Nginx ----
FROM nginx:1.27-alpine AS runtime

ENV FRONTEND_INTERNAL_PORT=80 \
    BACKEND_HOST=backend \
    BACKEND_PORT=5000

COPY --from=build /build/dist/angular-conduit /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE ${FRONTEND_INTERNAL_PORT}


CMD ["nginx", "-g", "daemon off;"]
