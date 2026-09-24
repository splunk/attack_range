FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY app/package*.json ./

# Install dependencies (node_modules from host are excluded via .dockerignore)
RUN npm ci

# Copy app source (excludes node_modules, dist, .astro via .dockerignore)
COPY app/ ./

# Build the Astro app
ENV DOCKER=true
ENV NODE_ENV=production
RUN npm run build

# Expose port
EXPOSE 4321

# Set port environment variable
ENV PORT=4321
ENV HOST=0.0.0.0

# Run the built Node.js server
CMD ["node", "./dist/server/entry.mjs"]
