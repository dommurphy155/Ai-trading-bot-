import logging
import traceback
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - FAILSAFE - %(message)s")


def global_exception_handler(exctype, value, tb):
    logging.critical(
        "UNCAUGHT EXCEPTION - triggering auto-repair!",
        exc_info=(
            exctype,
            value,
            tb))
    try:
        subprocess.run(["/bin/bash", "./repair.sh"], check=True)
        logging.info("Repair script executed")
    except Exception as e:
        logging.error(f"Repair script failed: {e}")
    finally:
        sys.exit(1)


sys.excepthook = global_exception_handler
logging.info("Failsafe active with auto-repair")
