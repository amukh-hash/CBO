import sys
from PIL import Image

def remove_checkerboard(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    data = img.getdata()
    
    new_data = []
    # Both colors of the checkerboard pattern (light grey and white)
    # The light grey is approx (204, 204, 204) or #CCCCCC
    # The white is approx (255, 255, 255)
    
    # We will use a tolerance to catch variations in the checkerboard
    tolerance = 15
    for item in data:
        r, g, b, a = item
        
        # Check if color is close to white
        is_white = abs(r - 255) < tolerance and abs(g - 255) < tolerance and abs(b - 255) < tolerance
        # Check if color is close to light grey (204, 204, 204 in many checkerboards)
        is_grey = abs(r - 204) < tolerance and abs(g - 204) < tolerance and abs(b - 204) < tolerance
        
        # It looks like the screenshot has a slightly bluish/greyish checkerboard
        # Let's check for any pixel where r,g,b are very close to each other (grayscale) 
        # and lightness is high enough
        is_grayscale = abs(r - g) < 10 and abs(r - b) < 10 and abs(g - b) < 10
        is_light = r > 180 and g > 180 and b > 180
        
        # Check if the pixel has low saturation (grey/white) and high value
        # This will target the checkerboard without affecting the brown tree
        if is_grayscale and is_light:
            new_data.append((255, 255, 255, 0)) # Make it transparent
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python make_transparent.py <input.jpg> <output.png>")
        sys.exit(1)
    remove_checkerboard(sys.argv[1], sys.argv[2])
    print(f"Saved {sys.argv[2]}")
