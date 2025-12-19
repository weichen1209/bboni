#!/usr/bin/env python
"""
互動式半導體科普遊戲 - 啟動腳本
"""

import sys
import os

# 確保路徑正確
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.main import main

if __name__ == "__main__":
    main()
