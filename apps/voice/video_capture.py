import cv2
import time
import os
import re
import pytesseract
from PIL import Image
import pyautogui
import numpy as np
from PIL import ImageGrab
import requests
from config import OPENAI_API_KEY
from tts import *

# Set the OpenAI API key in the environment variables
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Define the model to use - comment one out
model = "gpt-3.5-turbo"
model = "gpt-4-1106-preview"

# pip install opencv-python, tysseract, pyautogui

# Define the subfolder name
subfolder = "captured_frames"
script_dir = os.path.dirname(os.path.realpath(__file__))
subfolder_path = os.path.join(script_dir, subfolder)
# Check if the subfolder exists, if not, create it
if not os.path.exists(subfolder_path):
    os.makedirs(subfolder_path)

# Initialize video capture
# cap = cv2.VideoCapture(0)  # Adjust the device ID as necessary
# print("Video capture initialized.")

frame_count = 0  # Counter for the number of frames captured
max_frames =  3  # Maximum number of frames to capture
filename_base = "frame_"

def ocr_image(image_path):
    img = Image.open(image_path)  # Load the image with PIL
    #text = pytesseract.image_to_string(img)  # Perform OCR using pytesseract

    # Convert the image to a numpy array and then to grayscale
    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get a binary image
    # You can adjust the threshold value and method as needed
    _, binary = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)
    
    # Save the grayscale image
    grayscale_image_path = image_path.rsplit('.', 1)
    grayscale_image_path = f"{grayscale_image_path[0]}_grayscale.{grayscale_image_path[1]}"
    cv2.imwrite(grayscale_image_path, gray)
    # Save the binary image
    binary_image_path = image_path.rsplit('.', 1)
    binary_image_path = f"{binary_image_path[0]}_binary.{binary_image_path[1]}"
    cv2.imwrite(binary_image_path, binary)

    # Convert the binary image back to PIL format
    img = Image.fromarray(binary)
    
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(img, config=custom_config)
    
    # Print the identified text
    print("OCR IDENTIFIED TEXT:\n")
    print(text)
    return text

def immed_capture_from_window():
    global frame_count  # Ensure frame_count is used as a global variable
    
    # window_x = 900
    # window_y = 66
    # window_region = (window_x, window_y, window_x+600, window_y+340)  # LAPTOP
    window_x = 1700
    window_y = 66
    window_region = (window_x, window_y, window_x+800, window_y+500)  # LG Monitor
    
    # Immediately take a screenshot of the specified region
    screenshot = ImageGrab.grab(bbox=window_region)
    
    # Convert the screenshot to a format that OpenCV can work with
    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # Process the captured frame
    frame_filename = capture_frame_and_process(frame)
    return frame_filename
    # if process_time is False:
    #     print("Failed to capture frame.")
    # else:
    #     print(f"Frame captured.")

# Modify the capture_frame_and_process function to accept a frame directly
def capture_frame_and_process(frame=None):
    frame_num = get_next_frame_num("apps/voice/captured_frames","frame")
    print(f"Attempting to capture frame {frame_num}.")
    start_time = time.time()
    
    if frame is None:
        # Capture frame-by-frame from the video capture device
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame. Exiting...")
            return False  # Signal that frame capture failed
    
    print("Frame captured successfully.")
    
    # Process the frame (for now, we will save it as an image)
    frame_filename = os.path.join(subfolder_path, f"{filename_base}{frame_num:03}.png")  # Filename for the frame
    cv2.imwrite(frame_filename, frame)  # Save frame as PNG file
    print(f"Saved {frame_filename}")
    ocr_image(frame_filename)
    
    # Calculate processing time and return it
    process_time = time.time() - start_time
    print(f"Completed capture of {frame_filename}.")
    return frame_filename

def chat_completion_request(messages, model=model):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    json_data = {
        "model": model,
        "messages": messages
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response.json()  # Return the JSON response directly
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return None

def clean_ocr_text(ocr_text):
    messages = [
        {"role": "system", "content": "You are an expert at processing text. Given an OCR text input with potential noise and misspellings, extract and return only the actual character dialogue, omitting any extraneous characters or formatting. DO NOT include any quotation marks at the start or end of the response. If there are no discernible words in the input text, reply simply with 'No text'."},
        {"role": "user", "content": ocr_text}
    ]

    response = chat_completion_request(messages)
    if response:
        assistant_message = response['choices'][0]['message']['content']
        print("LLM RESPONSE - ASSISTANT MESSAGE:")
        print(assistant_message)
        return assistant_message
    else:
        return None

# OLD CODE FROM FIRST TRY WITH VIDEO DEVICE CAPTURE BOX
def capture_frame_and_process_device():
    global frame_count
    print(f"Attempting to capture frame {frame_count + 1}.")
    start_time = time.time()
    
    # Capture frame-by-frame
    ret, frame = cap.read()
    
    if not ret:
        print("Failed to capture frame. Exiting...")
        return False  # Signal that frame capture failed
    
    print("Frame captured successfully.")
    frame_count += 1  # Increment frame counter
    
    # Process the frame (for now, we will save it as an image)
    frame_filename = os.path.join(subfolder_path, f"{filename_base}{frame_count:03}.png")  # Filename for the frame
    cv2.imwrite(frame_filename, frame)  # Save frame as PNG file
    print(f"Saved {frame_filename}")
    perform_ocr(frame_filename)
    
    # Calculate processing time and return it
    process_time = time.time() - start_time
    print(f"Completed capture of frame {frame_count}.")
    return process_time

def auto_capture(sleep_time):
    try:
        while frame_count < max_frames:
            process_time = capture_frame_and_process()
            if process_time is False:
                break  # Exit if frame capture failed
            
            # Wait for a bit between captures - adjust as needed
            print(f"Waiting for {sleep_time} seconds before next capture.")
            time.sleep(max(0, sleep_time - process_time))  # Ensure at least sleep_time delay
            
            if frame_count >= max_frames:
                print("Reached maximum frame count. Exiting...")
                break
    finally:
        # Release the capture and close any open windows
        print("Releasing video capture and closing windows.")
        cap.release()
        cv2.destroyAllWindows()

def manual_capture():
    global frame_count  # Ensure frame_count is used as a global variable
    cv2.namedWindow("frame", cv2.WINDOW_NORMAL)  # Create a window named "frame"
    
    print("Press space to capture a frame or 'q' to quit.")
    try:
        while frame_count < max_frames:
            ret, frame = cap.read()  # Read a frame to display
            if not ret:
                print("Failed to read frame from capture device.")
                break
            
            cv2.imshow("frame", frame)  # Display the frame in the created window
            key = cv2.waitKey(1)  # Use a small delay to allow the window to process the incoming events
            
            if key == ord(' '):
                process_time = capture_frame_and_process()
                if process_time is False:
                    break  # Exit if frame capture failed
            elif key == ord('q'):
                print("Quitting capture.")
                break
            
            if frame_count >= max_frames:
                print("Reached maximum frame count. Exiting...")
                break
    finally:
        # Release the capture and close any open windows
        print("Releasing video capture and closing windows.")
        cap.release()
        cv2.destroyAllWindows()

def log_frame(log_file_path, frame_filename, text):
    with open(log_file_path, 'r+') as log_file:
        current_content = log_file.read()
        log_file.seek(0, 0)
        log_file.write(f"{frame_filename}\n{text}\n\n\n{current_content}")

def get_next_frame_num(folder_path, prefix):
    # Compile a regular expression pattern to match the file naming convention
    file_pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)[._]")

    max_num = 0
    # Iterate over all the files in the given folder_path
    for filename in os.listdir(folder_path):
        # Use the compiled regex pattern to search for matches in the filename
        match = file_pattern.search(filename)
        if match:
            # Extract the number from the filename and convert it to an integer
            num = int(match.group(1))
            # Update max_num if the current number is larger
            if num > max_num:
                max_num = num

    # Return the next number in the sequence
    return max_num + 1

if __name__ == "__main__":
    #manual_capture()
    #auto_capture(.5)

    cur_frame_path = immed_capture_from_window()
    cur_frame_filename = os.path.basename(cur_frame_path)
    ocr_text = ocr_image(cur_frame_path)
    #ocr_text = ocr_image("apps/voice/captured_frames/frame_001.png")
    clean_text = ' '.join(clean_ocr_text(ocr_text).splitlines())
    #play_tts_anyservice(clean_text)
    log_frame("apps/voice/frame_log.md", cur_frame_filename, clean_text)

