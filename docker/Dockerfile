# ============================================================
#  素珍管理系统 - Dockerfile
#  基于 nginx:alpine 托管前端静态页面
# ============================================================
FROM nginx:alpine

# 复制自定义 nginx 配置（路径相对于构建上下文，即项目根目录）
COPY docker/nginx.conf /etc/nginx/nginx.conf

# 复制前端静态文件到 nginx 默认发布目录
COPY frontend /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
