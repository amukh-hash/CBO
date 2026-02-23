import sys
from PIL import Image

def make_white_transparent(input_path, output_path, tolerance=240):
    img = Image.open(input_path).convert("RGBA")
    data = img.getdata()
    
    new_data = []
    for r, g, b, a in data:
        # Check against tolerance due to jpeg artifacts
        if r > tolerance and g > tolerance and b > tolerance:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append((r, g, b, a))
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved transparent image to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python make_jpg_transparent.py <input> <output>")
        sys.exit(1)
    make_white_transparent(sys.argv[1], sys.argv[2])
