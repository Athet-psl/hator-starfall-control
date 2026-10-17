"""Show one lighting slot of mode 9 (custom maps): slot.py N   |   slot.py restore"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experiment_ab as x

fd = os.open(x.node(), os.O_WRONLY)
try:
    frame = bytes([1, 0x0A, 2, 5]) if sys.argv[1] == "restore" else bytes([9, int(sys.argv[1]), 2, 5])
    x.put(fd, 10, frame + bytes(37))
    time.sleep(0.3)
    print("lighting now:", x.get(fd, 10, 41)[:4].hex(" "))
finally:
    os.close(fd)
