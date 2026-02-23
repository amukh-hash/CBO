from PIL import Image
import sys

def main():
    img_path = 'app/ui/static/Text_Number_Sheet.png'
    img = Image.open(img_path)
    print(f"Image size: {img.size}")
    
if __name__ == "__main__":
    main()
