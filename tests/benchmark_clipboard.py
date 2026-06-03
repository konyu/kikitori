import time
import pyperclip
from AppKit import NSPasteboard, NSStringPboardType

# warmup
pyperclip.copy("warmup")
pyperclip.paste()

# benchmark pyperclip
t0 = time.perf_counter()
for _ in range(100):
    pyperclip.copy("test")
    _ = pyperclip.paste()
t1 = time.perf_counter()
print(f"pyperclip (copy+paste x100): {(t1-t0)*1000:.2f} ms ({(t1-t0)*1000/100:.2f} ms/op)")

# benchmark NSPasteboard direct
board = NSPasteboard.generalPasteboard()

t0 = time.perf_counter()
for _ in range(100):
    board.clearContents()
    board.setString_forType_("test", NSStringPboardType)
    _ = board.stringForType_(NSStringPboardType)
t1 = time.perf_counter()
print(f"NSPasteboard direct (copy+paste x100): {(t1-t0)*1000:.2f} ms ({(t1-t0)*1000/100:.2f} ms/op)")
