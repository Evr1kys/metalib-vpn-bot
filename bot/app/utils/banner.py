"""
Banner and branding utilities
"""

METALIB_BANNER = """
╔═══════════════════════════════════════╗
║                                       ║
║        🛡️  MetaLib VPN                ║
║    Надежная защита вашей сети         ║
║                                       ║
╚═══════════════════════════════════════╝
"""

METALIB_BANNER_COMPACT = """
━━━━━━━━━━━━━━━━━━━━━━━━━
    🛡️ MetaLib VPN
━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def get_banner() -> str:
    """Get MetaLib VPN banner"""
    return METALIB_BANNER_COMPACT
