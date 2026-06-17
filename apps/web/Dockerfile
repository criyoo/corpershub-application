FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json /app/package.json
RUN npm install

FROM node:22-alpine AS dev
WORKDIR /app
ENV NODE_ENV=development
COPY package.json /app/package.json
COPY --from=deps /app/node_modules /app/node_modules
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules /app/node_modules
COPY . /app
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/public /app/public
COPY --from=builder /app/package.json /app/package.json
COPY --from=deps /app/node_modules /app/node_modules
EXPOSE 3000
CMD ["npm", "run", "start"]
