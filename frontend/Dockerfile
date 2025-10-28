FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev
COPY public ./public
COPY server.js .
ENV PORT=3000
CMD ["node", "server.js"]
