FROM node:22

WORKDIR /app
ARG API_BASE_URL=http://localhost:8000

# Step 1: install dependencies (better caching)
COPY package*.json ./
RUN npm ci

# Step 2: copy full source
COPY . .

# Step 3: inject production API domain at build time
RUN node -e "const fs=require('fs'); const p='src/environments/environment.prod.ts'; let s=fs.readFileSync(p,'utf8'); s=s.replace('https://your-api-domain.com', process.env.API_BASE_URL || '${API_BASE_URL}'); fs.writeFileSync(p,s);"

# Step 4: build Angular app
RUN npm run build

# Step 5: install static server
RUN npm install -g serve

# Step 6: expose port
EXPOSE 4200

# Step 7: serve correct dist folder
CMD ["serve", "-s", "dist/assessly-ui/browser", "-l", "4200"]
