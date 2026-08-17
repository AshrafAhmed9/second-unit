FROM node:20-slim AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN mkdir -p public
ARG _AGENT_URL
ENV NEXT_PUBLIC_AGENT_URL=${_AGENT_URL}
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
