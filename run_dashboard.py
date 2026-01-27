#!/usr/bin/env python3
"""Run the TD Realty Lead Engine web dashboard."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from td_lead_engine.web import create_app

if __name__ == '__main__':
    app = create_app()
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🏠 TD Realty Lead Engine Dashboard                      ║
    ║                                                           ║
    ║   Running at: http://localhost:5000                       ║
    ║                                                           ║
    ║   Login with any email/password to access the dashboard   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)
