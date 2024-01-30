"""
This script is a part of checkers pieces detector program.
This python script handles all image distortion preparation before the actual piece identifying.
"""

import cv2 as cv
import numpy as np
import imutils
 
W = 400 # board side length in pixels after preparatopion
X = 200 # board top left corner x position after preparation
Y = 100 # board top left corner y position after preparation


def select_point(event,x,y,flags,param):
    """ stores mouse position in global variables ix(for x coordinate) and iy(for y coordinate) on click inside the image"""
    global ix,iy
    if event == cv.EVENT_LBUTTONDOWN: # captures left button double-click
        ix,iy = x,y
        cv.destroyAllWindows()


def load_data():
    """loads data from txt files"""

    loaded_data = np.loadtxt('calibration_data.txt')
    loaded_camera_matrix = loaded_data[:9].reshape((3, 3))
    loaded_distortion_coeffs = loaded_data[9:]
    try:
        loaded_board_corners = np.loadtxt('board_corners.txt')
    except FileNotFoundError:
        loaded_board_corners = [[],[],[],[]]
    return loaded_camera_matrix, loaded_distortion_coeffs, loaded_board_corners


def initialize_global_values(initializing_img):
    """certain values need to be initialized before using other functions.
    This function needs to be called before anything else with an initializing image with the same size as the actual input frames
    """

    # Global values for easy use between functions
    global camera_matrix, distortion_coeffs, points, newcameramtx, roi
    # Load calibration data
    camera_matrix, distortion_coeffs, board_corners = load_data()

    points = board_corners
    # Extract camera matrix and distortion coefficients
    h,  w = initializing_img.shape[:2]
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(camera_matrix, distortion_coeffs, (w,h), 1, (w,h))


def calibrate_board_corners(undistorted_img):
    """calibrates the camera position. User needs to select board corners"""

    global points
    points = [[],[],[],[]]
    instructions = ["Pick upper left corner",
                "Pick upper right corner",
                "Pick lower left corner",
                "Pick lower right corner"]
    for i in range(0,4):

        cv.namedWindow(instructions[i])
        # bind select_point function to a window that will capture the mouse click
        cv.setMouseCallback(instructions[i], select_point)
        cv.imshow(instructions[i],undistorted_img)
        cv.waitKey(0) 
        points[i] = [ix, iy]

        cv.namedWindow(instructions[i])
        # bind select_point function to a window that will capture the mouse click
        cv.setMouseCallback(instructions[i], select_point)
        zoom_size = 20 # how much zoom is used to make the corner selection accurate
        zoom_img = undistorted_img[iy-zoom_size:iy+zoom_size, ix-zoom_size:ix+zoom_size]

        zoom_multiplier = 20 # how many times the pixels in the zoomed picture get multiplied
        zoom_img = imutils.resize(zoom_img, width=2*zoom_size*zoom_multiplier)

        cv.imshow(instructions[i],zoom_img)
        cv.waitKey(0)

        # the points should match the board corners in the original image
        points[i][0] = points[i][0]-zoom_size+int(ix/zoom_multiplier)
        points[i][1] = points[i][1]-zoom_size+int(iy/zoom_multiplier)

    np.savetxt('board_corners.txt', points)


def undistort_frame(frame):
    """undistorts a frame from the camera's internal lens distortions"""

    # undistort
    new_frame = cv.undistort(frame, camera_matrix, distortion_coeffs, None, newcameramtx)
    # crop the image
    x, y, w, h = roi
    new_frame = new_frame[y:y+h, x:x+w]
    return new_frame


def correct_perspective(frame):
    """corrects perspective of a undistorted frame using defined board corners (points)"""

    input_pts = np.float32(points)
    output_pts = np.float32([[X,Y],[X+W,Y],[X,Y+W],[X+W,Y+W]])
 
    # Compute the perspective transform M
    M = cv.getPerspectiveTransform(input_pts,output_pts)
 
    # Apply the perspective transformation to the image
    out = cv.warpPerspective(frame,M,(frame.shape[1], frame.shape[0]),flags=cv.INTER_LINEAR)

    return out


def prep_frame(frame, border=0):
    """only function needed after setup.
    undistorts, corrects perspective, makes border
    """

    uframe = undistort_frame(frame)
    pframe = correct_perspective(uframe)

    cropped_frame = pframe[Y-border:Y+W+border, X-border:X+W+border]
    return cropped_frame


# this needs to be done for everything else to work
# Picture is same size as the pictures camera has been calibrated with
img = cv.imread('initialization.jpg')
initialize_global_values(img)


