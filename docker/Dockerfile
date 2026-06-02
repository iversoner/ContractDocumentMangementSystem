# ============================================================
#  Suzhen Management System - Dockerfile
#  Based on nginx:alpine for serving frontend static files
# ============================================================
FROM nginx:alpine

# Copy custom nginx configuration (path relative to build context, i.e., project root)
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Copy frontend static files to nginx default directory
COPY frontend /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
