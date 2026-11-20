#!/bin/bash

cd "$(dirname "$0")" || exit 1

echo "SwasthyaVaani Auto-Sync Started"
echo "GitHub sync interval: 5 minutes"
echo "Press CTRL+C to stop."

while true; do

    if [[ -n "$(git status --porcelain)" ]]; then

        echo "Changes detected..."

        git add -A

        if ! git diff --cached --quiet; then

            git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')"

            if [ $? -eq 0 ]; then
                git push origin HEAD
            fi

        fi

    else
        echo "No changes found."
    fi

    echo "Waiting 5 minutes..."
    sleep 300

done