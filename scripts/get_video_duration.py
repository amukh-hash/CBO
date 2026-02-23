import subprocess
import sys

def get_duration(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    print(float(result.stdout))

if __name__ == "__main__":
    get_duration("app/ui/static/Start_Mia.mp4")
