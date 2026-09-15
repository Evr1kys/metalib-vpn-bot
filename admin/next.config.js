/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/admin',
  images: {
    unoptimized: true
  },
  trailingSlash: true,
  // Disable powered by header
  poweredByHeader: false,
}

module.exports = nextConfig
