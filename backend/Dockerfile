FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
ENV NODE_ENV=production
EXPOSE 4000
CMD ["node","src/index.js"]
