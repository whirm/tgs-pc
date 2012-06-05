#!/bin/sh

UIC=`which pyside-uic`
RCC=`which pyside-rcc`
set -e

if [ -z "$UIC" ]; then
    UIC=pyuic4
    RCC=pyrcc4
fi

cd ui
rm -f *.py *.pyc
touch __init__.py

$RCC resources.qrc -o resources_rc.py

for UI in *.ui ; do
    echo "Compiling $UI..."
    UIPY=$(echo $UI| sed 's/ui$/py/')
    $UIC $UI -o $UIPY
done
echo "All done!"
