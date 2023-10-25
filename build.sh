#!/bin/bash

rm -r ./dist
python3 -m build
#twine upload --repository-url TBD --verbose dist/*