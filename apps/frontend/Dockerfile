FROM node:20-alpine

WORKDIR /app/apps/frontend

COPY apps/frontend/package*.json ./
RUN npm install

COPY apps/frontend/ ./

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
