import code
import json

from robotd.native.apriltag._apriltag import ffi
import numpy as np
import math


def row_mul(m, corner, col):
    return m[col, 0] * corner[0] + m[col, 1] * corner[1] + m[col, 2]


def homography_transform(corner, homog):
    """
    Perform the equivalent of an OpenCV WarpPerspectiveTransform on the points
    See http://docs.opencv.org/2.4/modules/imgproc/doc/geometric_transformations.html#initundistortrectifymap
    for the equation.
    """
    z = row_mul(homog, corner, 2)
    x = row_mul(homog, corner, 0) / z
    y = row_mul(homog, corner, 1) / z
    return x, y


def decompose_homography(Homography, Calibration):
    """
    Python rewrite of the openCV function decomposeHomographyMat
    :param Homography:
    :param Calibration:
    :return: Rotation list, Translation List, Normals List
    """



def get_pixel_corners(homog):
    """
    Get the co-ordinate of the corners given the homography matrix
    :param homog: Numpy array Homography matrix as returned from Apriltags
    :return: list of (x,y) pixel co-ordinates of the corners of the token
    """
    # Define the corners of the marker
    corners = np.array([(-1, -1), (-1, 1), (1, 1), (1, -1)])

    transformed = []

    for corner in corners:
        x, y = homography_transform(corner, homog)
        transformed.append((x, y))

    return transformed


def get_pixel_centre(homography_matrix):
    """ Get the centre of the transform (ie how much translation there is)"""
    return homography_transform((0, 0), homography_matrix)


def get_cartesian(corner_pixels, focal_length, size):
    """ Convert the location of corner pixels to a 3D cartesian co-ordinate."""
    marker_width = size[0]
    # setup a
    a = np.array([[-corner_pixels[0][0], corner_pixels[1][0], corner_pixels[2][0]],
                  [-corner_pixels[0][1], corner_pixels[1][1], corner_pixels[2][1]],
                  [-focal_length, focal_length, focal_length]])
    # setup b
    b = np.array([[corner_pixels[3][0]], [corner_pixels[3][1]], [focal_length]])

    a_inv = np.linalg.inv(a)
    k_out = np.dot(a_inv, b)
    k0_over_k3 = k_out[0, 0]
    temp_k3 = math.sqrt(((-k0_over_k3 * a[0, 0] - b[0, 0]) ** 2) +
                        ((-k0_over_k3 * a[1, 0] - b[1, 0]) ** 2) +
                        ((-k0_over_k3 * focal_length - focal_length) ** 2))
    k3 = math.fabs(marker_width / temp_k3)
    k_list = [math.fabs(k_out[i, 0]) * k3 for i in range(3)]
    k_list.append(k3)
    cartesian = [(corner_pixels[i][0] * k_list[i], corner_pixels[i][1] * k_list[i], focal_length * k_list[i]) for i in
                 range(4)]
    print(cartesian)
    return cartesian


def get_distance_for_family_day(pixel_corners, focal_length, token_height):
    """HORRIBLE HACK."""
    pixel_height = (pixel_corners[1][1] - pixel_corners[0][1] + pixel_corners[2][1] - pixel_corners[3][1]) / 4
    return math.fabs(token_height * focal_length / pixel_height)


def get_distance(cartesian):
    x = (cartesian[0][0] + cartesian[1][0] + cartesian[2][0] + cartesian[3][0]) / 4
    y = (cartesian[0][1] + cartesian[1][1] + cartesian[2][1] + cartesian[3][1]) / 4
    z = (cartesian[0][2] + cartesian[1][2] + cartesian[2][2] + cartesian[3][2]) / 4
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


class Token:
    """ Class representing an apriltag Token"""
    def __init__(self, apriltag_detection, size, focal_length):
        # ID of the tag
        self.id = apriltag_detection.id
        self.size = size
        # Float from 0 to 1 on the quality of the token
        self.certainty = apriltag_detection.goodness
        arr = [apriltag_detection.H.data[x] for x in range(9)]
        homography = np.reshape(arr, (3, 3))
        self.pixel_corners = get_pixel_corners(homography)
        self.pixel_centre = get_pixel_centre(homography)
        # self.cartesian = get_cartesian(self.pixel_corners,focal_length,size)
        self.distance = get_distance_for_family_day(self.pixel_corners, focal_length, size[1])

    def __repr__(self):
        return "Token: {}, certainty:{}".format(self.id, self.certainty)
