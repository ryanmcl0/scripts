'''
Combine daily GPX track files from a trip into one GPX
'''

import glob
import gpxpy
import gpxpy.gpx
import os
import simplekml
import tempfile

def merge_with_waypoints_and_kml_limit(input_folder, output_prefix, gap_distance=0.0001, max_kml_size=5*1024*1024):
    """
    Merge multiple GPX files into one track (GPX stays intact).
    Adds a waypoint at the end of each file and a tiny gap in the track.
    Generates a KML file downsampled to fit under max_kml_size (default 5MB).
    """
    gpx_files = sorted(glob.glob(f"{input_folder}/*.gpx"))
    
    # --- GPX setup ---
    merged_gpx = gpxpy.gpx.GPX()
    merged_track = gpxpy.gpx.GPXTrack()
    merged_gpx.tracks.append(merged_track)
    merged_segment = gpxpy.gpx.GPXTrackSegment()
    merged_track.segments.append(merged_segment)

    # --- Collect all points for KML ---
    kml_points = []

    for file in gpx_files:
        with open(file, 'r') as f:
            gpx = gpxpy.parse(f)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        merged_segment.points.append(point)
                        kml_points.append((point.longitude, point.latitude, point.elevation or 0))

        # Add a waypoint at the last point with the file name
        if merged_segment.points:
            last_point = merged_segment.points[-1]
            wp = gpxpy.gpx.GPXWaypoint(
                latitude=last_point.latitude,
                longitude=last_point.longitude,
                elevation=last_point.elevation,
                name=os.path.basename(file)
            )
            merged_gpx.waypoints.append(wp)

            # Add a tiny "gap" in the GPX track
            gap_point = gpxpy.gpx.GPXTrackPoint(
                latitude=last_point.latitude + gap_distance,
                longitude=last_point.longitude + gap_distance,
                elevation=last_point.elevation
            )
            merged_segment.points.append(gap_point)
            kml_points.append((gap_point.longitude, gap_point.latitude, gap_point.elevation or 0))

        # --- Per-file status update ---
        print(f"Added {file} with waypoint and gap.")

    # --- Save GPX ---
    gpx_output_file = f"{output_prefix}.gpx"
    with open(gpx_output_file, 'w') as f:
        f.write(merged_gpx.to_xml())
    print(f"\n✅ GPX saved: {gpx_output_file}")

    # --- Create KML and downsample iteratively to fit max_kml_size ---
    sample_rate = 1
    while True:
        kml = simplekml.Kml()
        kml_track_coords = kml_points[::sample_rate]
        linestring = kml.newlinestring(name="Merged Track", coords=kml_track_coords)
        linestring.altitudemode = simplekml.AltitudeMode.relativetoground
        linestring.extrude = 1

        # Add waypoints to KML
        for file in gpx_files:
            last_point = merged_gpx.waypoints[[wp.name for wp in merged_gpx.waypoints].index(os.path.basename(file))]
            kml.newpoint(name=last_point.name, coords=[(last_point.longitude, last_point.latitude, last_point.elevation or 0)])

        # Save temporarily to check size
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            kml.save(tmp.name)
            size = os.path.getsize(tmp.name)
        if size <= max_kml_size:
            break
        sample_rate += 1

    kml_output_file = f"{output_prefix}.kml"
    kml.save(kml_output_file)
    print(f"✅ KML saved: {kml_output_file} (sampled every {sample_rate} points to fit {max_kml_size/1024/1024:.1f} MB)")

# --- Example usage ---
merge_with_waypoints_and_kml_limit(
    "/Users/ryanmcloughlin/Downloads/2025 China CNY GPX",
    "merged_track"
)