#!/usr/bin/env python3
"""ParaView visualization script for shock diamonds.

Load in ParaView: Tools -> Python Shell -> Run Script
Or: File -> Open -> select this file and choose "Python Script"
"""
from paraview.simple import *

# ---------------------------------------------------------------
# 1. Load the mirrored plume data
# ---------------------------------------------------------------
reader = OpenDataFile("output/merlin-1d/plume/flow_full.vtk")
Show(reader)

# ---------------------------------------------------------------
# 2. Calculate Pressure Ratio (P / P_ambient)
#    This highlights shocks much better than raw Mach
# ---------------------------------------------------------------
calc = Calculator(Input=reader)
calc.Function = "Pressure / 101325.0"
calc.ResultArrayName = "PressureRatio"
Show(calc)

# ---------------------------------------------------------------
# 3. Default view: Pressure Ratio contour
# ---------------------------------------------------------------
Display = GetDisplayProperties(calc)
Display.ColorArrayName = ["POINTS", "PressureRatio"]
Display.LookupTable = GetColorTransferFunction("PressureRatio")

# Set range to highlight shock structure (0.1 to 5.0 clips extremes)
prLUT = GetColorTransferFunction("PressureRatio")
prLUT.RescaleTransferFunction(0.1, 5.0)
prLUT.ApplyPreset("jet", True)

# Reset camera to show full domain
ResetCamera()
renderView1 = GetActiveViewOrCreate("RenderView")
renderView1.ResetCamera()

# ---------------------------------------------------------------
# 4. Add a second view for Mach number
# ---------------------------------------------------------------
# Create a new render view
renderView2 = CreateView("RenderView")
renderView2.ViewTime = GetAnimationScene().TimeKeeper.Time
renderView2.Light = ["", 0]
renderView2.CameraPosition = [6.0, 0.0, 30.0]
renderView2.CameraFocalPoint = [6.0, 0.0, 0.0]
renderView2.CameraViewUp = [0.0, 1.0, 0.0]

# Mach display in second view
machDisplay = Show(reader, renderView2)
machDisplay.ColorArrayName = ["POINTS", "Mach"]
machDisplay.LookupTable = GetColorTransferFunction("Mach")

machLUT = GetColorTransferFunction("Mach")
machLUT.RescaleTransferFunction(0.0, 6.0)
machLUT.ApplyPreset("jet", True)

# ---------------------------------------------------------------
# 5. Add a streamlines view
# ---------------------------------------------------------------
# Create streamline source along the axis
line = Line()
line.Point1 = [0.0, 0.0, 0.0]
line.Point2 = [12.0, 0.0, 0.0]
line.Resolution = 100

streamlines = StreamTracerWithCustomSource(Input=reader, SeedType=line)
streamlines.Vectors = ["POINTS", "Velocity"]
streamlines.MaximumStreamlineLength = 12.0

renderView3 = CreateView("RenderView")
renderView3.ViewTime = GetAnimationScene().TimeKeeper.Time
renderView3.CameraPosition = [6.0, 0.0, 20.0]
renderView3.CameraFocalPoint = [6.0, 0.0, 0.0]
renderView3.CameraViewUp = [0.0, 1.0, 0.0]

streamDisplay = Show(streamlines, renderView3)
streamDisplay.ColorArrayName = ["POINTS", "Mach"]
streamDisplay.LookupTable = GetColorTransferFunction("Mach")

# ---------------------------------------------------------------
# 6. Layout: 3 views side by side
# ---------------------------------------------------------------
layout = GetLayout()
layout.SplitHorizontal(0, 0.5)
layout.SplitVertical(1, 0.5)

# View 1: Pressure Ratio (top left)
AssignView(2, renderView1)
# View 2: Mach (top right)  
AssignView(3, renderView2)
# View 3: Streamlines (bottom)
layout.SplitHorizontal(5, 0.5)
AssignView(6, renderView3)

# ---------------------------------------------------------------
# 7. Screenshot
# ---------------------------------------------------------------
# SaveScreenshot("output/merlin-1d/plume/shock_diamonds.png",
#                magnification=2, quality=95)

print("=== Visualization loaded ===")
print("Views:")
print("  1. Pressure Ratio (P/P_ambient) - shows shock structure")
print("  2. Mach number - shows flow speed")
print("  3. Streamlines colored by Mach - shows flow pattern")
print()
print("Tips:")
print("  - Use 'Pressure Ratio' view to see shock diamonds")
print("  - Adjust 'Rescale Transfer Function' in Color Map Editor")
print("  - Try presets: 'jet', 'coolwarm', 'RdBu'")
print("  - Use 'Slice' filter to cut through the plume")
