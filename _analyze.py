from PIL import Image
import numpy as np

path = '/Users/kon_yu/Downloads/Gemini_Generated_Image_jjfhjbjjfhjbjjfh_removed_square.png'
img = Image.open(path)
arr = np.array(img)

alpha = arr[:, :, 3]
rgb = arr[:, :, :3]

is_opaque = alpha > 10
opaque_rgb = rgb[is_opaque]
opaque_brightness = np.mean(opaque_rgb, axis=1)

print("=== 不透明ピクセルの明度分布 ===")
print(f"総不透明ピクセル数: {len(opaque_brightness)}")
print(f"最小値: {opaque_brightness.min():.0f}")
print(f"最大値: {opaque_brightness.max():.0f}")
print(f"平均値: {opaque_brightness.mean():.1f}")
print(f"中央値: {np.median(opaque_brightness):.1f}")
print(f"標準偏差: {opaque_brightness.std():.1f}")

# ヒストグラム
for pct in [1, 5, 10, 25, 40, 50, 60, 75, 90, 95, 99]:
    val = np.percentile(opaque_brightness, pct)
    print(f"  {pct}パーセンタイル: {val:.0f}")

print()

# 複数閾値で試す
for thresh in [32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 200]:
    black = np.sum(opaque_brightness < thresh)
    white = np.sum(opaque_brightness >= thresh)
    print(f"閾値 {thresh:3d}: 黒={black:7d} ({100*black/len(opaque_brightness):.0f}%)  白={white:7d} ({100*white/len(opaque_brightness):.0f}%)")
