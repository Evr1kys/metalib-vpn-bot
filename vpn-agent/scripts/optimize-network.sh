#!/bin/bash
#
# VPN Server Network Optimization Script
# Increases throughput and reduces latency for VPN connections
#

set -e

echo "🚀 Optimizing network settings for VPN performance..."

# Backup current sysctl settings
cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d) 2>/dev/null || true

# Create optimization config
cat > /etc/sysctl.d/99-vpn-optimize.conf << 'EOF'
# ========================================
# VPN Performance Optimization
# ========================================

# === TCP Performance ===
# Increase TCP buffer sizes for high-throughput connections
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 67108864
net.ipv4.tcp_wmem = 4096 1048576 67108864

# Increase connection queue size
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# === TCP Fast Open ===
# Enable for both client and server
net.ipv4.tcp_fastopen = 3

# === TCP Congestion Control ===
# Use BBR for better performance (if available)
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# === Connection Reuse ===
# Enable TCP TIME_WAIT reuse
net.ipv4.tcp_tw_reuse = 1

# Reduce FIN timeout for faster connection cleanup
net.ipv4.tcp_fin_timeout = 15

# Reduce keepalive time
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5

# === Window Scaling ===
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1

# === Memory Tuning ===
net.ipv4.tcp_mem = 786432 1048576 1572864
net.ipv4.udp_mem = 786432 1048576 1572864

# === MTU Discovery ===
net.ipv4.tcp_mtu_probing = 1

# === IP Forwarding (required for VPN) ===
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# === Disable IPv6 if not used (optional) ===
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1

# === Reduce Latency ===
# Disable slow start after idle
net.ipv4.tcp_slow_start_after_idle = 0

# Enable low latency mode
net.ipv4.tcp_low_latency = 1

# === UDP Tuning ===
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192

# === Connection Tracking ===
# Increase conntrack table size for many VPN connections
net.netfilter.nf_conntrack_max = 1048576

# Reduce conntrack timeouts
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_udp_timeout = 60
net.netfilter.nf_conntrack_udp_timeout_stream = 180

# === ARP Cache ===
net.ipv4.neigh.default.gc_thresh1 = 4096
net.ipv4.neigh.default.gc_thresh2 = 8192
net.ipv4.neigh.default.gc_thresh3 = 16384

EOF

# Apply settings
echo "📝 Applying sysctl settings..."
sysctl -p /etc/sysctl.d/99-vpn-optimize.conf

# Check if BBR is available
if modprobe tcp_bbr 2>/dev/null; then
    echo "✅ TCP BBR congestion control enabled"
else
    echo "⚠️  BBR not available, using default congestion control"
    # Fallback to CUBIC if BBR is not available
    sysctl -w net.ipv4.tcp_congestion_control=cubic
fi

# Optimize network interface (if eth0 exists)
for iface in eth0 ens3 ens5 enp0s3; do
    if ip link show $iface >/dev/null 2>&1; then
        echo "🔧 Optimizing interface $iface..."
        
        # Increase ring buffer if supported
        ethtool -G $iface rx 4096 tx 4096 2>/dev/null || true
        
        # Enable TSO, GSO, GRO for better performance
        ethtool -K $iface tso on gso on gro on 2>/dev/null || true
        
        # Set interrupt coalescing for better throughput
        ethtool -C $iface rx-usecs 50 tx-usecs 50 2>/dev/null || true
        
        break
    fi
done

# Restart XRay to apply changes
if systemctl is-active --quiet xray; then
    echo "🔄 Restarting XRay..."
    systemctl restart xray
fi

echo ""
echo "✅ Network optimization complete!"
echo ""
echo "Current congestion control: $(sysctl -n net.ipv4.tcp_congestion_control)"
echo "TCP Fast Open: $(sysctl -n net.ipv4.tcp_fastopen)"
echo "IP Forwarding: $(sysctl -n net.ipv4.ip_forward)"
echo ""
echo "💡 For best results, ensure your VPN clients also have optimized settings."
