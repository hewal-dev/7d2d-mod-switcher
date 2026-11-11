#!/bin/bash
# Startet die Anwendung mit dem gebündelten Python.
export PYTHONDONTWRITEBYTECODE=1
exec "$APPDIR/opt/python{{ python-version }}/bin/python{{ python-version }}" \
     "$APPDIR/mod-switcher/mod_switcher.py" "$@"
