import cv2 as cv
import numpy as np
import imutils
import time
import os
import sys
from frame_prepping import prep_frame, calibrate_board_corners, undistort_frame


# lower and upper boundaries for HSV thresholds
black_treshold = 60
white_treshold = 230
BORDER = 20 # how big is the area around the board where pieces can be found
BOARD_SIZE = 244 # board side length in mm, needs to be correct to get correct coordinates

# additional arguments
# record saves the video the webcam records
# video uses the video as the webcam
# live is the default
modes = ['record', 'video', 'live']
mode = None

demo = False # visualizes more of thre process

if len(sys.argv) > 1 and sys.argv[1] in modes:
    mode = sys.argv[1]
else:
    mode = 'live'

if len(sys.argv) > 2 and sys.argv[2] == 'demo':
    demo = True


def prep(frame):
    """Takes distortion corrected frame as input 

    Returns mask of black pieces, mask of white pieces, and a resized frame
    """
    frame = imutils.resize(frame, width=2*BOARD_SIZE+2*BORDER)
    # gaussian blur
    blurred = cv.GaussianBlur(frame,(5,5),0)
    # Convert the image to gray scale
    gray = cv.cvtColor(blurred, cv.COLOR_BGR2GRAY)
    
    # Convert the image to HSV color space
    hsv = cv.cvtColor(blurred, cv.COLOR_BGR2HSV)

    # Define the lower and upper bounds of the blue color and yellow color
    # These are used to mask out blues that look like black and yellow that looks like white
    inverse_blue_mask = color_frame(hsv, [30, 50, 50], [180, 255, 255])
    inverse_yellow_mask = color_frame(hsv, [5, 50, 0], [70, 255, 255])
    

    # make masks and mask out all that can be mistaken for the wanted color
    black_mask = cv.inRange(gray,0,black_treshold)
    black_mask = cv.bitwise_and(black_mask, inverse_blue_mask)

    white_mask = cv.inRange(gray,white_treshold,255)
    white_mask = cv.bitwise_and(white_mask, inverse_yellow_mask)
    
    return black_mask, white_mask, frame


def color_frame(hsv_frame, lower, upper):
    """Returns the invers mask of the hsv color between lower and upper
    """

    # Define the lower and upper bounds of the blue color
    lower_color = np.array(lower, dtype=np.uint8)
    upper_color = np.array(upper, dtype=np.uint8)

    # Create a mask for the blue color
    mask = cv.inRange(hsv_frame, lower_color, upper_color)
    # Invert the blue mask
    inverse_mask = cv.bitwise_not(mask)

    return inverse_mask

### Find contours and display
def find_cnts(mask):
    """Rerturns all the contours of a mask image
    """
    cnts = cv.findContours(mask.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
   
    cnts = imutils.grab_contours(cnts)
    return cnts



def find_objects(mask, frame, color, obj_max_rad=50, obj_min_rad=25):
    """Finds all contours in a mask with a size between obj_min_rad and obj_max_rad.
    Returns a frame where the found objects are marked with circles with the given color and the centers of
    the objects in a list. Centers are given in (x mm, y mm) from the boards bottom left corner.
    """

    cnts = find_cnts(mask)
    frame1 = frame.copy()

    centers = []

    for i in range(len(cnts)):

        ((x, y), radius) = cv.minEnclosingCircle(cnts[i]) ## A different contour?
        
        if radius < obj_min_rad:
            continue
        if radius > obj_max_rad:
            continue
        # Find center of contour using moments in opencv
        M = cv.moments(cnts[i])
        if M["m00"] == 0:
            continue
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

        centers.append((23 + (center[0] - BORDER) / 2, 0, -23 - (2*BOARD_SIZE - center[1] + BORDER) / 2))

        #circle drawing
        cv.circle(frame1, (int(x), int(y)), int(radius),color, 2)
        cv.circle(frame1, center, 5, color, -1)

    # fill all pieces not found to be in position (6666,6666,0)
    while len(centers) < 12:
        centers.append((6666,6666,0))

    # returns only 12 first found pieces. Even if there were more
    return frame1, centers[:12]


if mode == 'video':
    cap = cv.VideoCapture('video.avi') #opens test video
else:
    cap = cv.VideoCapture(0, cv.CAP_DSHOW) #opens webcam

    # these are not needed with cap as video file
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv.CAP_PROP_EXPOSURE, -7.0)
    cap.set(cv.CAP_PROP_CONTRAST, 20)

if mode == 'record':
    # This is used to save a video file in correct format for remote work.
    # Define the codec and create VideoWriter object.The output is stored in 'outpy.avi' file.
    out = cv.VideoWriter('video.avi',cv.VideoWriter_fourcc('M','J','P','G'), 10, (1920,1080))

# Check if the webcam (or video) is opened correctly
if not cap.isOpened():
    raise IOError("Cannot open webcam or video")

# calibration not needed if the webcam or the board has not moved
if (input("Calibration not needed if setup has not changed \n"
          "Calibrate board: y/n: ") == 'y'):
    ret, frame = cap.read()
    calibrate_board_corners(undistort_frame(frame))

print(f"\nProgram has started in {mode} mode.\nPress Q in program window to quit")

# creates a new pieces file if one did not exist
with open('pieces.txt', 'w') as f:
    f.write('Create a new text file!')

# loops until q is pressed
while (cap.isOpened()):
    ret, frame = cap.read()

    if mode == 'record':
        out.write(frame)

    prepped_frame = prep_frame(frame, BORDER)

    black_mask, white_mask, prepped_frame = prep(prepped_frame)
    black_frame, black_centers = find_objects(black_mask, prepped_frame, (0,0,255))
    black_white_frame, white_centers = find_objects(white_mask, black_frame, (0,255,0))

    # these are just for demoing and visualizing the processed images
    if demo:
        cv.imshow('Input', frame)
        cv.imshow("black_mask", black_mask)
        cv.imshow("white_mask", white_mask)
        # print(f"Black pieces: {black_centers}")
        # print(f"White pieces: {white_centers}")

    cv.imshow('result', black_white_frame)

    tmpFile = 'tmp.txt'
    pieceFile = 'pieces.txt'

    # writes to a temp file to make the writing seem atomic
    # At least in Windows 10 needs to be run as administrator for reliable performance
    with open(tmpFile, 'w') as f:
        f.write(str(black_centers))
        f.write('\n')
        f.write(str(white_centers))
        # make sure that all data is on disk
        # see http://stackoverflow.com/questions/7433057/is-rename-without-fsync-safe
        f.flush()
        os.fsync(f.fileno())
        os.remove(pieceFile)
    os.rename(tmpFile, pieceFile)

    # checks for q and breaks the loop
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

# closes the webcam
cap.release()
if mode == 'record':
    out.release()
cv.destroyAllWindows()
