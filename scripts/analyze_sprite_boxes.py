from PIL import Image

def find_bounding_boxes(img_path):
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    data = img.getdata()
    
    # Simple projection to find columns
    cols_with_pixels = []
    for x in range(width):
        has_pixel = False
        for y in range(height):
            idx = y * width + x
            r, g, b, a = data[idx]
            # assume white/transparent is background
            if a > 10 and not (r > 240 and g > 240 and b > 240):
                has_pixel = True
                break
        cols_with_pixels.append(has_pixel)
        
    # Group columns into characters
    chars = []
    in_char = False
    start_x = 0
    for x, has_pixel in enumerate(cols_with_pixels):
        if has_pixel and not in_char:
            in_char = True
            start_x = x
        elif not has_pixel and in_char:
            in_char = False
            chars.append((start_x, x - 1))
            
    if in_char:
        chars.append((start_x, width - 1))
        
    print(f"Found {len(chars)} sprites by column projection.")
    for i, (start_x, end_x) in enumerate(chars):
        char_w = end_x - start_x + 1
        print(f"Sprite {i}: x={start_x} to {end_x}, width={char_w}")

if __name__ == "__main__":
    find_bounding_boxes('app/ui/static/Text_Number_Sheet.png')
