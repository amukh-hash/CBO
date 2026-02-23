from PIL import Image

def analyze_grid(img_path):
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    data = img.getdata()
    
    # projection to find rows
    rows_with_pixels = []
    for y in range(height):
        has_pixel = False
        for x in range(width):
            idx = y * width + x
            r, g, b, a = data[idx]
            if a > 10 and not (r > 240 and g > 240 and b > 240):
                has_pixel = True
                break
        rows_with_pixels.append(has_pixel)

    # projection to find cols
    cols_with_pixels = []
    for x in range(width):
        has_pixel = False
        for y in range(height):
            idx = y * width + x
            r, g, b, a = data[idx]
            if a > 10 and not (r > 240 and g > 240 and b > 240):
                has_pixel = True
                break
        cols_with_pixels.append(has_pixel)

    # Group into bounds
    def get_bounds(flags):
        bounds = []
        in_item = False
        start = 0
        for i, val in enumerate(flags):
            if val and not in_item:
                in_item = True
                start = i
            elif not val and in_item:
                in_item = False
                bounds.append((start, i - 1))
        if in_item:
            bounds.append((start, len(flags) - 1))
        return bounds

    row_bounds = get_bounds(rows_with_pixels)
    col_bounds = get_bounds(cols_with_pixels)
    
    print(f"Found {len(row_bounds)} rows.")
    for i, (sy, ey) in enumerate(row_bounds):
        print(f"Row {i}: y={sy} to {ey}, height={ey - sy + 1}")
        
    print(f"\nFound {len(col_bounds)} columns.")
    for i, (sx, ex) in enumerate(col_bounds):
        print(f"Col {i}: x={sx} to {ex}, width={ex - sx + 1}")

if __name__ == "__main__":
    analyze_grid('app/ui/static/Text_Number_Sheet.png')
