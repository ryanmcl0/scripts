import glob
import gpxpy
import gpxpy.gpx
import os
import simplekml
import tempfile
import math

def haversine(lon1, lat1, lon2, lat2):
    """Return distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def merge_with_waypoints_and_kml_limit(input_folder, gap_distance=0.0001, 
                                       max_kml_size=5*1024*1024, 
                                       split_gap_km=5):
    """
    Merge multiple GPX files into one track (GPX stays intact).
    Adds a waypoint at the end of each file.
    KML is split into multiple LineStrings if distance gap > split_gap_km.
    Downsamples until under max_kml_size (default 5 MB).
    """
    gpx_files = sorted(glob.glob(f"{input_folder}/*.gpx"))
    if not gpx_files:
        print("⚠️ No GPX files found in folder:", input_folder)
        return

    # Use folder name for output prefix
    output_prefix = os.path.basename(os.path.normpath(input_folder))

    # --- GPX setup ---
    merged_gpx = gpxpy.gpx.GPX()
    merged_track = gpxpy.gpx.GPXTrack()
    merged_gpx.tracks.append(merged_track)
    merged_segment = gpxpy.gpx.GPXTrackSegment()
    merged_track.segments.append(merged_segment)

    # --- KML collection (as multiple segments) ---
    kml_segments = []
    current_segment = []

    for file in gpx_files:
        with open(file, 'r') as f:
            gpx = gpxpy.parse(f)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        merged_segment.points.append(point)

                        pt = (point.longitude, point.latitude, point.elevation or 0)

                        # Split if big spatial gap
                        if current_segment:
                            last = current_segment[-1]
                            dist = haversine(last[0], last[1], pt[0], pt[1])
                            if dist > split_gap_km:
                                kml_segments.append(current_segment)
                                current_segment = []
                        current_segment.append(pt)

        # Add a waypoint at the last point
        if merged_segment.points:
            last_point = merged_segment.points[-1]
            wp = gpxpy.gpx.GPXWaypoint(
                latitude=last_point.latitude,
                longitude=last_point.longitude,
                elevation=last_point.elevation,
                name=os.path.basename(file)
            )
            merged_gpx.waypoints.append(wp)

            # Tiny artificial GPX gap (to visually separate segments in GPX)
            gap_point = gpxpy.gpx.GPXTrackPoint(
                latitude=last_point.latitude + gap_distance,
                longitude=last_point.longitude + gap_distance,
                elevation=last_point.elevation
            )
            merged_segment.points.append(gap_point)

        print(f"Added {file} with waypoint.")

    if current_segment:
        kml_segments.append(current_segment)

    # --- Save GPX ---
    gpx_output_file = os.path.join(input_folder, f"{output_prefix}.gpx")
    with open(gpx_output_file, 'w') as f:
        f.write(merged_gpx.to_xml())
    print(f"\n✅ GPX saved: {gpx_output_file}")

    # --- Create KML with multiple LineStrings ---
    sample_rate = 1
    while True:
        kml = simplekml.Kml()
        for seg in kml_segments:
            coords = seg[::sample_rate]
            if len(coords) > 1:
                line = kml.newlinestring(name="Merged Track", coords=coords)
                line.altitudemode = simplekml.AltitudeMode.relativetoground
                line.extrude = 1

        # Add waypoints to KML
        for wp in merged_gpx.waypoints:
            kml.newpoint(name=wp.name, coords=[(wp.longitude, wp.latitude, wp.elevation or 0)])

        # Save temporarily to check size
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            kml.save(tmp.name)
            size = os.path.getsize(tmp.name)
        if size <= max_kml_size:
            break
        sample_rate += 1

    kml_output_file = os.path.join(input_folder, f"{output_prefix}.kml")
    kml.save(kml_output_file)
    print(f"✅ KML saved: {kml_output_file} (split gaps > {split_gap_km} km, sampled every {sample_rate})")


# --- Example usage ---
if __name__ == "__main__":
    merge_with_waypoints_and_kml_limit(
        "/Users/ryanmcloughlin/Downloads/2025 China CNY North"
    )