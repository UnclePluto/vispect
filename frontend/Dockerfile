FROM node:24-alpine AS build
RUN npm install --global pnpm@10.33.0
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY frontend /app/frontend
COPY contracts /app/contracts
RUN pnpm build
FROM nginx:1.27-alpine
COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80
