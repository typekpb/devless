FROM oven/bun:1-slim

WORKDIR /app

# Copy package files
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --production

# Copy source, skills, and config
COPY config.yml ./
COPY src/ ./src/
COPY .agents/ ./.agents/

ENV NODE_ENV=production

ENTRYPOINT ["bun", "src/index.ts"]
