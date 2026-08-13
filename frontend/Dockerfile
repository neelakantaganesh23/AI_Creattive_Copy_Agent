# syntax=docker/dockerfile:1
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .

# Vite inlines these at build time, so they are build arguments rather than
# runtime environment variables.
ARG VITE_APP_NAME="AI Creative Copy Agent"
ARG VITE_API_BASE_URL="/api/v1"
ARG VITE_ENABLE_GOOGLE_LOGIN="false"
ARG VITE_ENABLE_DEMO_DATA="true"
ARG VITE_POLL_INTERVAL_MS="900"
ENV VITE_APP_NAME=$VITE_APP_NAME \
    VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_ENABLE_GOOGLE_LOGIN=$VITE_ENABLE_GOOGLE_LOGIN \
    VITE_ENABLE_DEMO_DATA=$VITE_ENABLE_DEMO_DATA \
    VITE_POLL_INTERVAL_MS=$VITE_POLL_INTERVAL_MS

RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --spider -q http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
