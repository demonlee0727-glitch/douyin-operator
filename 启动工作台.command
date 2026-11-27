#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
python3 app.py serve --open
result=$?
if [ "$result" != 0 ]; then read -r -p "按回车关闭窗口"; fi
exit "$result"

