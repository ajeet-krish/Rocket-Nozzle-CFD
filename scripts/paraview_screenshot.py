"""
Capture a single screenshot of all 4 RenderViews in the current ParaView layout.

Usage (Python Shell):
  1. Open ParaView
  2. Load your 4 engine VTU files, one per view (split into 2x2 layout)
  3. Set up Mach coloring, camera angles, etc. as desired
  4. Tools -> Python Shell -> Run Script -> select this file
"""

from paraview.simple import SaveScreenshot, GetLayout

OUTPUT = "/Users/ajeet/Projects/Rocket Nozzle CFD/docs/assets/images/mach_contour_all_engines.png"

layout = GetLayout()
if layout is None:
    print("ERROR: No layout found. Make sure you have views open.")
else:
    SaveScreenshot(OUTPUT, layout)
    print(f"Screenshot saved: {OUTPUT}")
