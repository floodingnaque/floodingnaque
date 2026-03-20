FROM nginx:stable-alpine

# Generate Diffie-Hellman parameters at build time (takes ~30s)
RUN apk add --no-cache openssl \
  && openssl dhparam -out /etc/nginx/dhparam.pem 2048 \
  && apk del openssl

# Entrypoint: start nginx and periodically reload to pick up renewed certs
# Certbot renews every 12h; nginx reloads every 6h to pick up new certs
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
