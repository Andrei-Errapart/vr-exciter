"""Rectify the HDD underside photo and print feature positions in mm.

The photo (disk/hdd-photos/07-hdd-underside-width-ruler.jpg) is taken at an
angle, and the rulers lie on the table about 26 mm below the drive's underside,
so their scale does not apply to it. Instead, the four SFF-8301 bottom
mounting holes give an exact homography for the underside plane:

    SFF-8301 Rev 1.9, Table 3-1: A4 = 95.25 mm (left-right spacing),
    A7 = 41.28 mm (connector end to the first pair), A6 = 44.45 mm (to the second pair).

Drive frame (bottom view as photographed): X to the right from the drive's
centre line, Y down from the connector end. This is also the PCB's aux/grid
origin (KiCad position 150, 40 mm).

The pixel centres below were fitted to the bright hole rims with OpenCV
(threshold + least-squares circle). Needs opencv-python and numpy.

    python3 rectify_underside.py PHOTO [OUT.png]

Writes the rectified image (10 px/mm, X -56..56, Y -8..154) if OUT is given.
"""
import sys

import cv2
import numpy as np

# pixel centres in the EXIF-rotated photo (3072 x 4096)
SFF_PX = {4: (687.8, 1464.6), 5: (2131.8, 1465.2), 9: (698.0, 2142.1), 10: (2128.0, 2130.3)}
SFF_MM = {4: (-47.625, 41.28), 5: (47.625, 41.28), 9: (-47.625, 85.73), 10: (47.625, 85.73)}
SCREW_PX = {1: (748.3, 1099.0), 2: (1668.3, 1067.8), 3: (1669.1, 1312.6), 6: (770.4, 1802.9),
            7: (1280.6, 1702.9), 8: (1887.2, 1791.2)}

# Measured in the rectified image (mm, drive frame):
#   spindle axis (Hough fit of the large circle): X 0.2, Y 95.9, circle radius ~20
#   spring contact dimples, 1..3: (-11.83, 63.67), (-9.83, 63.17), (-7.87, 62.60)
#   -> 2.0 mm pitch, ~6.0 mm from screw 7 along the spring strip, strip tilted 13.5 deg
#   flat area for the PCB: X -36..38, Y 12..88 (side-rail bulges near SFF holes 4/5,
#   chamfer of the recess from X 38.5 at the top right)


def homography():
    src = np.float32([SFF_PX[k] for k in (4, 5, 9, 10)])
    dst = np.float32([SFF_MM[k] for k in (4, 5, 9, 10)])
    return cv2.getPerspectiveTransform(src, dst)


def main():
    H = homography()
    for k, (x, y) in SCREW_PX.items():
        v = H @ np.array([x, y, 1.0])
        print(f"screw hole {k}: X {v[0] / v[2]:7.2f}  Y {v[1] / v[2]:7.2f} mm")
    if len(sys.argv) > 2:
        img = cv2.imread(sys.argv[1])               # cv2 applies the EXIF rotation
        s, x0, y0 = 10.0, -56.0, -8.0
        T = np.array([[s, 0, -x0 * s], [0, s, -y0 * s], [0, 0, 1]])
        cv2.imwrite(sys.argv[2], cv2.warpPerspective(img, T @ H, (1120, 1620), flags=cv2.INTER_CUBIC))
        print("wrote", sys.argv[2])


if __name__ == "__main__":
    main()
