FROM node:22-alpine

WORKDIR /app

COPY package.json tsconfig.json next.config.ts next-env.d.ts ./
COPY src ./src

RUN npm install
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-p", "3000"]
