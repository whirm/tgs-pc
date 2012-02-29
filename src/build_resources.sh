#!/bin/sh

cd ui
pyuic4 main.ui -o main.py
pyrcc4 resources.qrc -o resources_rc.py

