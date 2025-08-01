for f in "$@"
do
  if [[ -f "$f" ]]; then
    dir=$(dirname "$f")
    filename=$(basename "$f")
    extension="${filename##*.}"
    base="${filename%.*}"

    # Create subfolder
    outdir="$dir/Compressed"
    mkdir -p "$outdir"

    output="$outdir/${base}_compressed.jpg"

    echo "Compressing: $filename → $output"
    sips -s format jpeg -s formatOptions 60 "$f" --out "$output" >/dev/null

    # Check if output was created
    if [[ -f "$output" ]]; then
      echo "Compressed: $output"
    else
      echo "Failed to compress: $f"
    fi
  else
    echo "Not a file: $f"
  fi
done