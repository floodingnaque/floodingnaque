# syntax=docker/dockerfile:1
# =====================================================
# Floodingnaque Frontend - Multi-stage Dockerfile
# =====================================================
# Build: docker build -t floodingnaque-frontend:latest .
# Run:   docker run -p 3000:3000 floodingnaque-frontend:latest
# =====================================================

# ===================
# Build Arguments
# ===================
ARG NODE_VERSION=22

# =====================================================
# Stage 1: Dependencies - Install node_modules
# =====================================================
FROM node:${NODE_VERSION}-alpine AS deps

WORKDIR /app

# Copy package files for dependency installation
COPY package.json package-lock.json ./

# Install dependencies (clean install for reproducibility)
RUN npm ci --ignore-scripts

# =====================================================
# Stage 2: Builder - Build the application
# =====================================================
FROM node:${NODE_VERSION}-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build argument for API base URL (injected at build time)
ARG VITE_API_BASE_URL=http://localhost:5000
ARG VITE_APP_NAME=Floodingnaque
ARG VITE_ENABLE_SSE=true

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_NAME=${VITE_APP_NAME}
ENV VITE_ENABLE_SSE=${VITE_ENABLE_SSE}

# Build the application
RUN npm run build

# =====================================================
# Stage 3: Production - Serve with Nginx
# =====================================================
FROM nginx:1.28-alpine AS production

LABEL maintainer="Floodingnaque Team" \
    description="Floodingnaque Flood Prediction Frontend" \
    org.opencontainers.image.source="https://github.com/floodingnaque/floodingnaque"

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root user (nginx image runs as nginx by default)
# Ensure proper permissions on html directory
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    # Create cache directories with proper permissions
    mkdir -p /var/cache/nginx /var/run && \
    chown -R nginx:nginx /var/cache/nginx /var/run

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

# =====================================================
# Stage 4: Development - Hot-reload dev server
# =====================================================
FROM node:${NODE_VERSION}-alpine AS development

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies)
RUN npm ci

# Copy source code (overridden by volume mount in compose)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
