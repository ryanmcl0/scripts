for f in "$@"
do
    # Get filename without extension, keep full path
    BASENAME="${f%.*}"
    
    # Detect audio codec using ffprobe
    CODEC=$(/opt/homebrew/bin/ffprobe -v error -select_streams a:0 -show_entries stream=codec_name \
      -of default=nw=1:nk=1 "$f")

    # Choose extension based on codec
    case "$CODEC" in
        aac)
            EXT="m4a"
            ;;
        mp3)
            EXT="mp3"
            ;;
        pcm_s16le | pcm_s24le)
            EXT="wav"
            ;;
        *)
            EXT="m4a"  # Default fallback
            ;;
    esac

    # Set output file in same folder
    OUTPUT="${BASENAME}_audio.${EXT}"
    
    # Extract audio without re-encoding
    /opt/homebrew/bin/ffmpeg -i "$f" -vn -acodec copy "$OUTPUT"
done