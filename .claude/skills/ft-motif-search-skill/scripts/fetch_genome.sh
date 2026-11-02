#!/usr/bin/env bash
# Fetch the GRCm39 RefSeq genome + GFF3 from this repo's GitHub Release.
#
# The genome is too large for git, and NCBI is unreachable from sandboxes with
# an outbound allowlist, so a bgzipped copy is attached to a GitHub Release
# (release-assets.githubusercontent.com is usually allowlisted). This script
# downloads it, verifies SHA256SUMS, and decompresses into the layout that
# check_genome.py expects (the NCBI metadata JSONs are already in git).
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

for f in SHA256SUMS "${FASTA}.gz" "${GFF}.gz"; do
    [ -s "$f" ] && [ "$f" != SHA256SUMS ] && { echo "have $f"; continue; }
    echo "downloading $f"
    curl -fL --retry 3 -o "$f" "${BASE}/${f}"
done

# only the two .gz files are needed here; .gzi/.fai lines are skipped
grep -E " (${FASTA}|${GFF})\.gz$" SHA256SUMS | sha256sum -c -

# decompress (gzip reads bgzip); the notebook and check_genome.py use plain files
[ -s "$FASTA" ] || gzip -dc "${FASTA}.gz" > "$FASTA"
[ -s "$GFF" ]   || gzip -dc "${GFF}.gz"   > "$GFF"
rm -f "${FASTA}.gz" "${GFF}.gz"

ls -la
