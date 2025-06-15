#!/usr/bin/env bash
echo "Installing Python 3.10.13 manually..."
pyenv install 3.10.13
pyenv global 3.10.13
pip install -r requirements.txt