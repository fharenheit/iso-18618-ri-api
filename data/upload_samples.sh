#!/bin/bash
# Upload all 10 sample IDS submissions to the API
# Usage: ./data/upload_samples.sh [BASE_URL]
#   BASE_URL defaults to http://localhost:8000

set -e

BASE_URL="${1:-http://localhost:8000}"
API="${BASE_URL}/api/v1/submissions"
DIR="$(cd "$(dirname "$0")" && pwd)"
FILES_DIR="${DIR}/files"

echo "=== Generating dummy attachment files ==="
python3 "${DIR}/generate_files.py"
echo ""

echo "=== Uploading 10 sample IDS submissions to ${API} ==="
echo ""

# 01 - Single Crown
echo "[01] Single Crown"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/01-single-crown.ids" \
  -F "files=@${FILES_DIR}/upper_jaw_scan.stl" \
  -F "files=@${FILES_DIR}/lower_jaw_scan.stl" \
  -F "files=@${FILES_DIR}/bite_registration.stl" \
  -o /dev/null

# 02 - Bridge
echo "[02] 3-Unit Bridge"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/02-bridge-three-unit.ids" \
  -F "files=@${FILES_DIR}/mandible_prep_scan.stl" \
  -F "files=@${FILES_DIR}/maxilla_opposing.stl" \
  -o /dev/null

# 03 - Implant
echo "[03] Implant Abutment"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/03-implant-abutment.ids" \
  -F "files=@${FILES_DIR}/implant_site_scan.stl" \
  -F "files=@${FILES_DIR}/cbct_dicom.zip" \
  -o /dev/null

# 04 - Veneer
echo "[04] Veneer Case (6 units)"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/04-veneer-case.ids" \
  -F "files=@${FILES_DIR}/upper_prep_scan.stl" \
  -F "files=@${FILES_DIR}/lower_opposing.stl" \
  -F "files=@${FILES_DIR}/smile_photo_front.jpg" \
  -F "files=@${FILES_DIR}/smile_design_mockup.stl" \
  -o /dev/null

# 05 - Inlay/Onlay
echo "[05] Inlay & Onlay"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/05-inlay-onlay.ids" \
  -F "files=@${FILES_DIR}/quadrant_2_prep.stl" \
  -F "files=@${FILES_DIR}/quadrant_2_opposing.stl" \
  -o /dev/null

# 06 - Removable Partial Denture
echo "[06] Removable Partial Denture"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/06-removable-partial-denture.ids" \
  -F "files=@${FILES_DIR}/upper_arch_edentulous.stl" \
  -F "files=@${FILES_DIR}/lower_arch_full.stl" \
  -F "files=@${FILES_DIR}/bite_registration.stl" \
  -o /dev/null

# 07 - Orthodontic Appliance
echo "[07] Orthodontic Aligner"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/07-orthodontic-appliance.ids" \
  -F "files=@${FILES_DIR}/upper_arch_stage5.stl" \
  -F "files=@${FILES_DIR}/lower_arch_stage5.stl" \
  -F "files=@${FILES_DIR}/treatment_plan.pdf" \
  -o /dev/null

# 08 - Full Denture
echo "[08] Full Denture Set"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/08-full-denture.ids" \
  -F "files=@${FILES_DIR}/upper_edentulous_ridge.stl" \
  -F "files=@${FILES_DIR}/lower_edentulous_ridge.stl" \
  -F "files=@${FILES_DIR}/jaw_relation_record.stl" \
  -F "files=@${FILES_DIR}/facebow_record.pdf" \
  -o /dev/null

# 09 - Multi-case Broker
echo "[09] Multi-case Broker (3 patients)"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/09-multi-case-broker.ids" \
  -F "files=@${FILES_DIR}/yang_upper_scan.stl" \
  -F "files=@${FILES_DIR}/yang_lower_scan.stl" \
  -F "files=@${FILES_DIR}/moon_upper_scan.stl" \
  -F "files=@${FILES_DIR}/moon_lower_scan.stl" \
  -F "files=@${FILES_DIR}/ryu_implant_scan.stl" \
  -o /dev/null

# 10 - Notification (no files)
echo "[10] Notification Status Update"
curl -s -w "  HTTP %{http_code}\n" -X POST "${API}" \
  -F "ids_xml=@${DIR}/10-notification-status-update.ids" \
  -o /dev/null

echo ""
echo "=== Done ==="
echo "View dashboard: ${BASE_URL}/"
echo "View submissions: ${BASE_URL}/submissions"
