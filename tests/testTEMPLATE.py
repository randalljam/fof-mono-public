# Run tests with python -m unittest discover -s tests

import os
import sys
# Add the parent directory to the Python path so we can import the 'general' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import shutil
import tempfile

from core.fileops import *
# Optional template imports (transcribe pulls in opencv/cv2):
# from core.transcribe import *
# from core.llm import *
# from core.structured import *


# LEAVE THIS AS A REFERENCE FOR EVALUATING FAILS
# AssertionError: 'Returned' != 'Expected'

if __name__ == '__main__':
    unittest.main()