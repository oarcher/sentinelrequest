#!/bin/bash
script_dir=$(dirname $(readlink -f $0))
jupyter nbconvert --to markdown --execute --output-dir=$script_dir $script_dir/README.ipynb