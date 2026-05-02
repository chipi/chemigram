#!/bin/bash
# Empirical evidence script for the Path-B / iop_order finding (RFC-018).
# See README.md in this directory for context + outcomes.
#
# Tests five Path B scenarios with iop_order absent from per-entry
# metadata. Renders each, byte-compares to a baseline. Identical bytes
# would mean darktable silently dropped the entry; differing bytes mean
# the entry was applied.
#
# Reproduces against the Phase 0 raw + configdir.

set -euo pipefail

RAW="${CHEMIGRAM_TEST_RAW:-$HOME/chemigram-phase0/raws/raw-test.NEF}"
CFG="${CHEMIGRAM_DT_CONFIGDIR:-$HOME/chemigram-phase0/dt-config}"

if [[ ! -f "$RAW" ]]; then
    echo "skip: $RAW not found (set CHEMIGRAM_TEST_RAW)"
    exit 0
fi
if [[ ! -d "$CFG" ]]; then
    echo "skip: $CFG not found (set CHEMIGRAM_DT_CONFIGDIR)"
    exit 0
fi
if ! command -v darktable-cli >/dev/null 2>&1; then
    echo "skip: darktable-cli not on PATH"
    exit 0
fi

WORK=$(mktemp -d -t chemigram-preflight-XXXXXX)
trap 'rm -rf "$WORK"' EXIT
cp "$RAW" "$WORK/input.NEF"
cd "$WORK"

# Real op_params from existing v3 reference fixtures
EXPO_PARAMS="00000000000080b90000003f00004842000080c00100000001000000"
TEMP_PARAMS="0090ec3f0000803f0020bb3f0000000004000000"
CMRGB_PARAMS="gz04eJxjYGiwZ8AAxIqRD9iAmAmIWYCYEYg9GQ7Z6TMftDunX+sKsosRKg8AihYHRg=="
GRAIN_PARAMS="0000a040000080400000a043"
VIGNETTE_PARAMS="0000003f0000003f9a99993e0000c03f0000a0bf000080bf0000000000000000000080bf"

# Helper to render a XMP and report status
render() {
    local label="$1"
    local out="$2"
    darktable-cli input.NEF input.NEF.xmp "$out" \
        --width 256 --height 256 --hq false \
        --apply-custom-presets false \
        --core --configdir "$CFG" 2>&1 \
        | grep -iE "exported|drop|error|warn" | head -3
}

# Baseline: just one exposure entry at mp=0
write_baseline_xmp() {
    cat > input.NEF.xmp <<XMP
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:darktable="http://darktable.sf.net/"
    darktable:rating="0" darktable:auto_presets_applied="0"
    darktable:history_end="1" darktable:iop_order_version="4">
   <darktable:history>
    <rdf:Seq>
     <rdf:li darktable:num="0" darktable:operation="exposure"
       darktable:enabled="1" darktable:modversion="6"
       darktable:params="$EXPO_PARAMS"
       darktable:multi_name="" darktable:multi_priority="0"
       darktable:blendop_version="14" darktable:blendop_params=""/>
    </rdf:Seq>
   </darktable:history>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
XMP
}

# Path B test: append a second history entry with NO iop_order set
write_pathb_xmp() {
    local op="$1" modv="$2" params="$3" mp="$4" mname="$5"
    cat > input.NEF.xmp <<XMP
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:darktable="http://darktable.sf.net/"
    darktable:rating="0" darktable:auto_presets_applied="0"
    darktable:history_end="2" darktable:iop_order_version="4">
   <darktable:history>
    <rdf:Seq>
     <rdf:li darktable:num="0" darktable:operation="exposure"
       darktable:enabled="1" darktable:modversion="6"
       darktable:params="$EXPO_PARAMS"
       darktable:multi_name="" darktable:multi_priority="0"
       darktable:blendop_version="14" darktable:blendop_params=""/>
     <rdf:li darktable:num="1" darktable:operation="$op"
       darktable:enabled="1" darktable:modversion="$modv"
       darktable:params="$params"
       darktable:multi_name="$mname" darktable:multi_priority="$mp"
       darktable:blendop_version="14" darktable:blendop_params=""/>
    </rdf:Seq>
   </darktable:history>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
XMP
}

write_baseline_xmp; render "baseline" baseline.jpg

write_pathb_xmp vignette 3 "$VIGNETTE_PARAMS" 0 ""
render "vignette (new op)" vignette.jpg

write_pathb_xmp grain 1 "$GRAIN_PARAMS" 0 ""
render "grain (new op)" grain.jpg

write_pathb_xmp exposure 6 "$EXPO_PARAMS" 1 "extra"
render "exposure mp=1 (new instance)" expo_mp1.jpg

write_pathb_xmp temperature 4 "$TEMP_PARAMS" 1 "extra_wb"
render "temperature mp=1 (new instance)" temp_mp1.jpg

write_pathb_xmp channelmixerrgb 3 "$CMRGB_PARAMS" 1 "extra_color"
render "channelmixerrgb mp=1 (new instance)" cmrgb_mp1.jpg

echo
echo "=== Path B finding: iop_order is NOT required in dt 5.4.1 ==="
echo "Each Path B test should differ from baseline (entry applied):"
for f in vignette grain expo_mp1 temp_mp1 cmrgb_mp1; do
    a=$(md5 -q baseline.jpg)
    b=$(md5 -q "$f.jpg")
    if [[ "$a" == "$b" ]]; then
        echo "  $f: SAME as baseline (entry was DROPPED!)"
        exit 1
    else
        echo "  $f: differs from baseline (entry applied) ✓"
    fi
done
echo
echo "All five Path B scenarios applied without per-entry iop_order."
echo "See README.md for analysis."
