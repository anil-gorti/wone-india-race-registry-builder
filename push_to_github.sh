#!/bin/bash
# push_to_github.sh
# ==================
# Run this once to create the GitHub repo and push.
# 
# Usage:
#   chmod +x push_to_github.sh
#   ./push_to_github.sh
#
# You'll be prompted for:
#   - GitHub username
#   - Personal Access Token (needs repo scope)
#   - Repo name (default: wone-race-registry)
#   - Visibility (public/private)

set -e

echo ""
echo "WONE Race Registry - GitHub Push"
echo "================================="
echo ""

# Collect inputs
read -p "GitHub username: " GITHUB_USER
read -s -p "Personal Access Token (repo scope): " GITHUB_TOKEN
echo ""
read -p "Repo name [wone-race-registry]: " REPO_NAME
REPO_NAME=${REPO_NAME:-wone-race-registry}
read -p "Visibility (public/private) [private]: " VISIBILITY
VISIBILITY=${VISIBILITY:-private}

PRIVATE="true"
if [ "$VISIBILITY" = "public" ]; then
    PRIVATE="false"
fi

echo ""
echo "Creating repo: $GITHUB_USER/$REPO_NAME ($VISIBILITY)..."

# Create repo via GitHub API
CREATE_RESPONSE=$(curl -s -w "%{http_code}" \
  -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"private\":$PRIVATE,\"description\":\"Historical race registry scraper for India endurance sports timing platforms. Part of WONE coordination infrastructure.\"}")

HTTP_STATUS="${CREATE_RESPONSE: -3}"
RESPONSE_BODY="${CREATE_RESPONSE:0:${#CREATE_RESPONSE}-3}"

if [ "$HTTP_STATUS" = "201" ]; then
    echo "Repo created successfully."
elif [ "$HTTP_STATUS" = "422" ]; then
    echo "Repo already exists. Pushing to existing repo..."
else
    echo "Error creating repo (HTTP $HTTP_STATUS):"
    echo "$RESPONSE_BODY"
    exit 1
fi

# Set remote and push
REMOTE_URL="https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git push -u origin main

echo ""
echo "Done! Repo available at:"
echo "  https://github.com/$GITHUB_USER/$REPO_NAME"
