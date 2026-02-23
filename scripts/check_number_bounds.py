import os
from PIL import Image

def analyze():
    img_path = 'app/ui/static/Text_Number_Sheet.png'
    img = Image.open(img_path).convert("RGBA")
    
    data = img.getdata()
    new_data = []
    tolerance = 240
    for r, g, b, a in data:
        if r > tolerance and g > tolerance and b > tolerance:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    
    xbounds = [(0, 270), (270, 413), (413, 579), (579, 745), (745, 917), (917, 1083), (1083, 1408)]
    
    for i in range(7):
        left, right = xbounds[i]
        cropped = img.crop((left, 0, right, 368))
        bbox = cropped.getbbox()
        print(f"Num {i} bbox: {bbox}")

    for i, col in [(7, 0), (8, 5), (9, 4)]:
        left, right = xbounds[col]
        cropped = img.crop((left, 368, right, 736))
        bbox = cropped.getbbox()
        print(f"Num {i} bbox: {bbox} (rel to y=368)")

if __name__ == "__main__":
    analyze()
