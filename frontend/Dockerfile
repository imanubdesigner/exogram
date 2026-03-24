FROM node:20-alpine

WORKDIR /app

# Copiar package files
COPY package*.json ./

# npm ci garantiza instalación reproducible desde package-lock.json.
RUN npm ci && chown -R node:node /app/node_modules

# Copiar código y transferir propiedad al usuario node (uid 1000, incluido
# en la imagen base). Correr como non-root limita el blast radius ante un RCE.
COPY --chown=node:node . .

USER node

# Exponer puerto de Vite
EXPOSE 5173

# Comando por defecto
CMD ["npm", "run", "dev", "--", "--host"]
