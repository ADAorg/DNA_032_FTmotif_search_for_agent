#!/usr/bin/env bash
# Fetch the GRCm39 RefSeq genome + GFF3 from this repo's GitHub Release.
#
# The genome is too large for git, and NCBI is unreachable from sandboxes with
# an outbound allowlist, so a bgzipped copy is attached to a GitHub Release
# (release-assets.githubusercontent.com is usually allowlisted). This script
# downloads it and verifies SHA256SUMS. The files are kept compressed: pyfaidx
# and pyranges read the bgzipped FASTA (with its .gzi/.fai) and gzipped GFF
# directly, and unpacking needs ~3.7 GB, more than a sandbox usually has.
# check_genome.py verifies this layout in its compressed mode.
#
# Plain files already in place (e.g. on the analysis server) are left alone.
#
# Usage: fetch_genome.sh [refseq_dir]   (default: Data/ncbi_dataset_RefSeq_GCF_000001635.27)
set -euo pipefail

REPO="ADAorg/DNA_032_FTmotif_search_for_agent"
TAG="genome-GRCm39-GCF_000001635.27"
BASE="https://github.com/${REPO}/releases/download/${TAG}"
DEST="${1:-Data/ncbi_dataset_RefSeq_GCF_000001635.27}"

FASTA="GCF_000001635.27_GRCm39_genomic.fna"
GFF="genomic.gff"

mkdir -p "$DEST"
cd "$DEST"

if [ -s "$FASTA" ] && [ -s "$GFF" ]; then
    echo "plain genome already present in $DEST; run check_genome.py to verify it"
    exit 0
fi

REQUIRED=("${FASTA}.gz" "${FASTA}.gz.gzi" "${GFF}.gz")
# the .fai only saves time: pyfaidx rebuilds it on first use (~30 s) if absent
OPTIONAL="${FASTA}.gz.fai"

have_all() { for f in "${REQUIRED[@]}"; do [ -s "$f" ] || return 1; done; }

curl -fsSL --retry 3 -o SHA256SUMS "${BASE}/SHA256SUMS"
if have_all && sha256sum -c --quiet --ignore-missing SHA256SUMS 2>/dev/null; then
    echo "compressed genome already present and verified in $DEST"
    exit 0
fi

for f in "${REQUIRED[@]}"; do
    echo "downloading $f"
    curl -fL --retry 3 -o "$f" "${BASE}/${f}"
done
echo "downloading $OPTIONAL (optional)"
curl -fL --retry 3 -o "$OPTIONAL" "${BASE}/${OPTIONAL}" \
    || { rm -f "$OPTIONAL"; echo "no $OPTIONAL in the release; pyfaidx will build it on first use"; }

# --ignore-missing: the optional .fai may be absent; every required file was
# downloaded above with curl -f, so it is present and gets checked
sha256sum -c --ignore-missing SHA256SUMS

df -h . | tail -1
ls -la
