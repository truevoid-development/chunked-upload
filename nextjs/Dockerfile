FROM node:22

WORKDIR /app

COPY package.json .
COPY package-lock.json .

RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
