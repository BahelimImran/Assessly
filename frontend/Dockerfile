FROM node:22

WORKDIR /app

# Step 1: install dependencies (better caching)
COPY package*.json ./
RUN npm install

# Step 2: copy full source
COPY . .

# Step 3: build Angular app
RUN npm run build

# Step 4: install static server
RUN npm install -g serve

# Step 5: expose port
EXPOSE 4200

# Step 6: serve correct dist folder
CMD ["serve", "-s", "dist/", "-l", "4200"]