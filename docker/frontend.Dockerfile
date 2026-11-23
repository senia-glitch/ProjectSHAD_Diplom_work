# syntax=docker/dockerfile:1
ARG NODE_VERSION=24
FROM node:${NODE_VERSION}-bookworm-slim AS dependencies
WORKDIR /frontend
RUN chown node:node /frontend
USER node
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM dependencies AS source
COPY --chown=node:node frontend/ ./

FROM source AS test
CMD ["npm", "test"]

FROM source AS build
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.28-alpine AS runtime
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
