#!/usr/bin/env python3
"""
CS4348 Project 3 - B-Tree Index File Manager
Author: Annie Li
"""

import sys
import os
import struct
import csv

# Constants
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

# Low-level I/O helpers
def _pack8(n: int) -> bytes:
    """Pack a single unsigned 64-bit integer big-endian."""
    return n.to_bytes(8, 'big')


def _unpack8(data: bytes, offset: int = 0) -> int:
    """Unpack a single unsigned 64-bit integer big-endian."""
    return int.from_bytes(data[offset:offset + 8], 'big')


def _read_block(f, block_id: int) -> bytes:
    f.seek(block_id * BLOCK_SIZE)
    data = f.read(BLOCK_SIZE)
    if len(data) != BLOCK_SIZE:
        raise IOError(f"Short read on block {block_id}")
    return data


def _write_block(f, block_id: int, data: bytes):
    assert len(data) == BLOCK_SIZE
    f.seek(block_id * BLOCK_SIZE)
    f.write(data)
    f.flush()

# Header helpers 
def _build_header(root_id: int, next_block: int) -> bytes:
    """Construct the header block."""
    data = bytearray(BLOCK_SIZE)
    buf[0:8]   = MAGIC
    buf[8:16]  = _pack8(root_id)
    buf[16:24] = _pack8(next_block)
    return bytes(buf)


def _read_header(f):
    """Returns (root_id, next_block)."""
    data = _read_block(f, 0)
    if data[0:8] != MAGIC:
        sys.exit("Error: Not a valid index file (bad magic number).")
    root_id    = _unpack8(data, 8)
    next_block = _unpack8(data, 16)
    return root_id, next_block


def _write_header(f, root_id: int, next_block: int):
    _write_block(f, 0, _build_header(root_id, next_block))


# Node helpers
class BNode:
    """In-memory representation of one B-tree node block."""

    def __init__(self, block_id: int, parent_id: int,
                 keys=None, values=None, children=None):
        self.block_id  = block_id
        self.parent_id = parent_id
        self.keys      = list(keys)     if keys     else []
        self.values    = list(values)   if values   else []
        self.children  = list(children) if children else [0] * MAX_CHILDREN

    @property
    def n(self):
        return len(self.keys)

    @property
    def is_leaf(self):
        return all(c == 0 for c in self.children)

    def serialize(self) -> bytes:
        buf = bytearray(BLOCK_SIZE)
        struct.pack_into('>Q', buf, NODE_ID_OFF,     self.block_id)
        struct.pack_into('>Q', buf, NODE_PARENT_OFF, self.parent_id)
        struct.pack_into('>Q', buf, NODE_NKEYS_OFF,  self.n)
        for i, k in enumerate(self.keys):
            struct.pack_into('>Q', buf, NODE_KEYS_OFF + i * 8, k)
        for i, v in enumerate(self.values):
            struct.pack_into('>Q', buf, NODE_VALS_OFF + i * 8, v)
        for i, c in enumerate(self.children[:MAX_CHILDREN]):
            struct.pack_into('>Q', buf, NODE_CHLD_OFF + i * 8, c)
        return bytes(buf)

    def _load_node(f, block_id: int) -> BNode:
    return BNode.deserialize(_read_block(f, block_id))


def _save_node(f, node: BNode):
    _write_block(f, node.block_id, node.serialize())


def _alloc_node(f, next_block: int, root_id: int,
                parent_id: int) -> tuple:
    """Allocate a new empty node at next_block, update header, return (node, new_next)."""
    node = BNode(next_block, parent_id)
    _save_node(f, node)
    new_next = next_block + 1
    _write_header(f, root_id, new_next)
    return node, new_next

# B-Tree operations (<= 3 nodes in memory, no splitting or merging)

def _split_child(f, parent: BNode, child_index: int,
                 root_id: int, next_block: int) -> tuple:
    """
    Split parent.children[child_index] (which is full).
    Returns (updated root_id, updated next_block).
    Only parent + child + new_sibling are in memory simultaneously.
    """
    child = _load_node(f, parent.children[child_index])   # node 2

    t = MIN_DEGREE
    mid_key = child.keys[t - 1]
    mid_val = child.values[t - 1]

    # Build the new right sibling
    new_sib = BNode(next_block, parent.block_id)           # node 3
    new_sib.keys     = child.keys[t:]
    new_sib.values   = child.values[t:]
    new_sib.children = child.children[t:] + [0] * t
    next_block += 1

    # Trim the left child
    child.keys     = child.keys[:t - 1]
    child.values   = child.values[:t - 1]
    child.children = child.children[:t] + [0] * t

    # Insert median into parent
    parent.keys.insert(child_index, mid_key)
    parent.values.insert(child_index, mid_val)
    parent.children.insert(child_index + 1, new_sib.block_id)
    # Keep children list exactly MAX_CHILDREN long
    parent.children = parent.children[:MAX_CHILDREN]

    # Update parent pointers for new sibling's children
    if not new_sib.is_leaf:
        for cid in new_sib.children:
            if cid != 0:
                gc = _load_node(f, cid)
                gc.parent_id = new_sib.block_id
                _save_node(f, gc)

    _save_node(f, child)
    _save_node(f, new_sib)
    _save_node(f, parent)
    _write_header(f, root_id, next_block)

    return root_id, next_block


def _insert_nonfull(f, node: BNode, key: int, value: int,
                    root_id: int, next_block: int) -> tuple:
    """
    Insert (key, value) into the subtree rooted at node,
    which is guaranteed to be non-full.
    Returns (root_id, next_block).
    Memory: node + up to 1 child + 1 new node = ≤ 3.
    """
    i = node.n - 1

    if node.is_leaf:
        # Simple insert into leaf
        node.keys.append(0)
        node.values.append(0)
        while i >= 0 and key < node.keys[i]:
            node.keys[i + 1]   = node.keys[i]
            node.values[i + 1] = node.values[i]
            i -= 1
        node.keys[i + 1]   = key
        node.values[i + 1] = value
        _save_node(f, node)
        return root_id, next_block
    else:
        # Find child to descend into
        while i >= 0 and key < node.keys[i]:
            i -= 1
        i += 1
        child = _load_node(f, node.children[i])  # 2nd node in memory
        if child.n == MAX_KEYS:
            root_id, next_block = _split_child(f, node, i, root_id, next_block)
            # After split, re-check which child to go into
            if key > node.keys[i]:
                i += 1
        child = _load_node(f, node.children[i])  # reload (may have changed)
        return _insert_nonfull(f, child, key, value, root_id, next_block)

