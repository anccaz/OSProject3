#!/usr/bin/env python3
"""
CS4348 Project 3 - B-Tree Index File Manager
Author: Annie Li
"""

import sys
import os
import struct
import csv

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
BLOCK_SIZE      = 512
MAGIC           = b"4348PRJ3"
MIN_DEGREE      = 10                   # t = 10  →  max 19 keys, 20 children
MAX_KEYS        = 2 * MIN_DEGREE - 1   # 19
MAX_CHILDREN    = 2 * MIN_DEGREE       # 20

# Header layout  (all offsets within block 0)
HDR_MAGIC_OFF   = 0
HDR_ROOT_OFF    = 8
HDR_NEXT_OFF    = 16

# Node layout  (within a 512-byte block)
NODE_ID_OFF     = 0
NODE_PARENT_OFF = 8
NODE_NKEYS_OFF  = 16
NODE_KEYS_OFF   = 24                          # 19 × 8 = 152 bytes
NODE_VALS_OFF   = 24 + MAX_KEYS * 8           # 176
NODE_CHLD_OFF   = 24 + MAX_KEYS * 8 * 2      # 328  (20 × 8 = 160 bytes)


