from PIL import Image
import os

def extract():
    img_path = 'app/ui/static/Text_Number_Sheet.png'
    out_dir = 'app/ui/static/numbers'
    os.makedirs(out_dir, exist_ok=True)
    
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
    
    # Accurate Col bounds to split digits exactly without overlaps
    xbounds = [
        (0, 270),    # Col 0 (0 and 7)
        (270, 413),  # Col 1 (1)
        (413, 579),  # Col 2 (2)
        (579, 745),  # Col 3 (3)
        (745, 917),  # Col 4 (4 and 9)
        (917, 1083), # Col 5 (5 and 8)
        (1083, 1408) # Col 6 (6)
    ]
    
    # Uniform height bounds: Crop straight to the 200px visual height
    # Top row is 135 to 330
    # Bottom row is 375 to 570
    top_y1 = 135
    top_y2 = 330
    
    bot_y1 = 375
    bot_y2 = 570
    
    # Top row: 0 1 2 3 4 5 6
    for i in range(7):
        left, right = xbounds[i]
        num_img = img.crop((left, top_y1, right, top_y2))
        num_img.save(os.path.join(out_dir, f"{i}.png"))
        
    # Bottom row mapping:
    # Col 0 -> 7
    # Col 5 -> 8
    # Col 4 -> 9
    img.crop((xbounds[0][0], bot_y1, xbounds[0][1], bot_y2)).save(os.path.join(out_dir, "7.png"))
    img.crop((xbounds[5][0], bot_y1, xbounds[5][1], bot_y2)).save(os.path.join(out_dir, "8.png"))
    img.crop((xbounds[4][0], bot_y1, xbounds[4][1], bot_y2)).save(os.path.join(out_dir, "9.png"))
    
    print("Done extracting cleanly cropped 0-9")

if __name__ == "__main__":
    extract()
