import cv2
import numpy as np

def analyze():
    cap = cv2.VideoCapture('app/ui/static/Start_Mia.mp4')
    ret, frame = cap.read()
    if not ret:
        print("Failed to read video")
        return
    
    cv2.imwrite("first_frame.png", frame)
    
    # Print colors of a few top-left pixels
    print("Top-left block:", frame[0:10, 0:10])
    print("Some other block:", frame[50:60, 50:60])
    
    # Let's count the most frequent colors in the first frame
    reshaped = frame.reshape(-1, 3)
    unique_colors, counts = np.unique(reshaped, axis=0, return_counts=True)
    sorted_idx = np.argsort(counts)[::-1]
    print("Top 10 frequent colors:")
    for i in range(10):
        print(unique_colors[sorted_idx[i]], counts[sorted_idx[i]])

if __name__ == "__main__":
    analyze()
