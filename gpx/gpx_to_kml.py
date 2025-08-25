import gpxpy
import simplekml
import os
import tempfile

def gpx_to_kml_maxdetail(gpx_file, max_kml_size=5*1024*1024):
    """
    Convert a single GPX file to a KML file.
    Ensures KML is under max_kml_size (default 5MB),
    keeping as much data as possible.
    Output is saved in a 'Tracks' folder in the same directory as this script.
    """
    if not os.path.isfile(gpx_file):
        raise FileNotFoundError(f"GPX file not found: {gpx_file}")

    with open(gpx_file, 'r') as f:
        gpx = gpxpy.parse(f)

    # Collect track points
    kml_points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                kml_points.append((point.longitude, point.latitude, point.elevation or 0))

    if not kml_points:
        raise ValueError("No track points found in GPX file.")

    # Try full detail first
    sample_rate = 1
    size = 0
    while True:
        kml = simplekml.Kml()
        coords = kml_points[::sample_rate]
        linestring = kml.newlinestring(
            name=os.path.basename(gpx_file),
            coords=coords
        )
        linestring.altitudemode = simplekml.AltitudeMode.relativetoground
        linestring.extrude = 1

        # Save temporarily and check size
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            kml.save(tmp.name)
            size = os.path.getsize(tmp.name)

        if size <= max_kml_size:
            break
        sample_rate += 1  # downsample more if too big

    # Ensure Tracks folder exists in same directory as script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tracks_dir = os.path.join(script_dir, "Tracks")
    os.makedirs(tracks_dir, exist_ok=True)

    # Build output path
    base_name = os.path.splitext(os.path.basename(gpx_file))[0] + ".kml"
    output_file = os.path.join(tracks_dir, base_name)

    # Save final KML
    kml.save(output_file)
    print(f"✅ KML saved: {output_file}")
    print(f"   - Final size: {size/1024/1024:.2f} MB")
    print(f"   - Kept 1 in {sample_rate} points ({len(kml_points)//sample_rate} of {len(kml_points)} points)")

# --- Example usage ---
gpx_to_kml_maxdetail("/Users/ryanmcloughlin/Downloads/Day_19_Bayannur_Wuyuan_Urad_Middle_Banner_Bayan_Obo_Damao_Banner.gpx")
