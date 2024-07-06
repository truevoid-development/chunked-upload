FROM node:22

WORKDIR /app

COPY . .

RUN npm install

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
