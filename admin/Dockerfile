# Use pre-built files (build locally before docker build)
FROM nginx:alpine

# Copy pre-built files directly
COPY out /usr/share/nginx/html/admin

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
