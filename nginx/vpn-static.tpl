#=========================================================================#
# VPN Static Site Template with API Proxy (HTTP)                          #
#=========================================================================#

server {
        listen      %ip%:%proxy_port%;
        server_name %domain_idn% %alias_idn%;
        
        include %home%/%user%/conf/web/%domain%/nginx.forcessl.conf*;
        
        location ~ /\.(?!well-known\/|file) {
                deny all;
                return 404;
        }

        location / {
            return 301 https://$host$request_uri;
        }
}
