#!/bin/bash
{
    echo "Starting script at $(date)"
    source /home/cpat/PycharmProjects/budwire_site_test/budwire_site_test/.venv/bin/activate
    python3 /home/cpat/PycharmProjects/budwire_site_test/budwire_site_test/budwire_site_test.py
    deactivate
    echo "Script finished at $(date)"
} >> /path/to/logfile.log 2>&1
