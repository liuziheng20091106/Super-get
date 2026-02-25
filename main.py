import sys
import traceback
from main_window import main
from logger import log_crash

def global_exception_handler(exc_type, exc_value, exc_traceback):
    log_crash(exc_type, exc_value, exc_traceback)
    traceback.print_exception(exc_type, exc_value, exc_traceback)

if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    main()