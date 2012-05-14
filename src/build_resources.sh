#!/bin/sh

set -e

cd ui
rm *.py *.pyc
touch __init__.py

pyrcc4 resources.qrc -o resources_rc.py

for UI in *.ui ; do
    echo "Compiling $UI..."
    UIPY=$(echo $UI| sed 's/ui$/py/')
    pyuic4 $UI -o $UIPY
done
echo "All done!"
