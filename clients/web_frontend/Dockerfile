FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json ./

# Install dependencies (ignoring errors if lock file is missing)
RUN npm install

# Copy source code
COPY . .

# Build Next.js
ARG NEXT_PUBLIC_API_URL
RUN npm run build

# Production Stage
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next

EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["npm", "start"]
