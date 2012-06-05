#!/usr/bin/python
# -*- coding: utf-8 -*-

from tgs_pc import main


if __name__ == "__main__":
    exit_exception = None
    chat = main.ChatCore()
    chat.run()
    if exit_exception:
        raise exit_exception
