import time
import math
import tobii_research as tr
from pythonosc import udp_client
import argparse
import sys

# OSC Configuration
DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 6731

def gaze_data_callback(gaze_data, client):
    """
    Callback function that is called every time new gaze data is received.
    Streams the data via OSC.
    """
    # Extract left and right gaze points on the display area (normalized 0.0 to 1.0)
    # In tobii_research, gaze_data is an object with attributes
    left_eye = gaze_data.left_gaze_point_on_display_area
    right_eye = gaze_data.right_gaze_point_on_display_area

    lx, ly = left_eye
    rx, ry = right_eye

    # Check for validity (NaN indicates the eye was not tracked)
    valid_l = not (math.isnan(lx) or math.isnan(ly))
    valid_r = not (math.isnan(rx) or math.isnan(ry))

    if valid_l and valid_r:
        # Calculate average gaze point
        avg_x = (lx + rx) / 2.0
        avg_y = (ly + ry) / 2.0

        # Send average gaze (Normalized 0.0 to 1.0)
        client.send_message("/Tobii/gaze_x", float(avg_x))
        client.send_message("/Tobii/gaze_y", float(avg_y))

        # Compatibility with OpenFace 3.0 / OpenFace Lite addresses
        # OpenFace Lite expects approximate degrees.
        # Map 0.5 center to 0, 0.0 to -30, 1.0 to 30.
        # Note: Y is usually inverted in screen space (0 top, 1 bottom)
        client.send_message("/OpenFace/gaze_left_right", float((avg_x - 0.5) * 60.0))
        client.send_message("/OpenFace/gaze_up_down", float((avg_y - 0.5) * -60.0))

    if valid_l:
        client.send_message("/Tobii/left/gaze_x", float(lx))
        client.send_message("/Tobii/left/gaze_y", float(ly))

    if valid_r:
        client.send_message("/Tobii/right/gaze_x", float(rx))
        client.send_message("/Tobii/right/gaze_y", float(ry))

    # Optional: Pupil Diameter
    lp = gaze_data.left_pupil_diameter
    rp = gaze_data.right_pupil_diameter
    if not math.isnan(lp):
        client.send_message("/Tobii/left/pupil_diameter", float(lp))
    if not math.isnan(rp):
        client.send_message("/Tobii/right/pupil_diameter", float(rp))

def main():
    parser = argparse.ArgumentParser(description='Stream Tobii PCEye 5 gaze data to OSC')
    parser.add_argument('--ip', type=str, default=DEFAULT_IP, help='OSC Destination IP (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='OSC Destination Port (default: 6731)')
    args = parser.parse_args()

    client = udp_client.SimpleUDPClient(args.ip, args.port)

    print("Searching for Tobii eye trackers...")
    try:
        found_eyetrackers = tr.find_all_eyetrackers()
    except Exception as e:
        print(f"Error searching for eye trackers: {e}")
        sys.exit(1)

    if len(found_eyetrackers) == 0:
        print("No Tobii eye trackers found!")
        print("\nTroubleshooting:")
        print("1. Ensure the Tobii Runtime (or TD Control for PCEye 5) is running.")
        print("2. Check if the device is plugged in and calibrated.")
        print("3. Note: The consumer 'Eye Tracker 5' is NOT supported by this SDK unless it has a Pro Upgrade.")
        sys.exit(1)

    eyetracker = found_eyetrackers[0]
    print(f"--- Connected Device ---")
    print(f"Model: {eyetracker.model}")
    print(f"Serial: {eyetracker.serial_number}")
    print(f"Address: {eyetracker.address}")
    print(f"------------------------")
    print(f"Streaming gaze data to {args.ip}:{args.port}...")
    print("Press Ctrl+C to stop.")

    # Subscribe to gaze data
    # Note: as_dictionary is not supported in the standard tobii_research SDK
    eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA,
                            lambda x: gaze_data_callback(x, client))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)
        print("Successfully unsubscribed from eye tracker.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
