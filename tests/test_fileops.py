# Run tests with python -m unittest discover -s tests

import os
import sys
# Add the parent directory to the Python path so we can import the 'core' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tempfile
import unittest
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch, mock_open, MagicMock, call
import calendar

from core.fileops import *

print_get_timestamp_flag = False

### INITIAL
class TestVerbosePrint(unittest.TestCase):  # mocks print
    @patch('builtins.print')
    def test_verbose_print__prints_single_correctly(self, mock_print):
        # Test that verbose_print prints the correct messages when verbose is True
        verbose_print(True, "Test single message")
        mock_print.assert_called_once_with("Test single message")

    @patch('builtins.print')
    def test_verbose_print__prints_multiple_correctly(self, mock_print):
        # Test that verbose_print prints the correct messages when verbose is True
        verbose_print(True, "Test message", "with multiple arguments")
        mock_print.assert_called_once_with("Test message", "with multiple arguments")

    @patch("builtins.print")
    def test_verbose_print__verbose_true_prints_messages(self, mock_print):
        verbose = True
        messages = ("This", "is", "a", "test.")
        verbose_print(verbose, *messages)
        
        # Verify that print was called with the messages when verbose is True
        mock_print.assert_called_once_with(*messages)

    @patch("builtins.print")
    def test_verbose_print__verbose_false_does_not_print(self, mock_print):
        verbose = False
        messages = ("This", "is", "a", "test.")
        verbose_print(verbose, *messages)
        
        # Verify that print was not called when verbose is False
        mock_print.assert_not_called()

    def test_verbose_print__raises_type_error_for_non_bool_verbose(self):
        with self.assertRaises(TypeError) as context:
            verbose_print("not a boolean", "This should fail.")
        self.assertEqual(str(context.exception), "The first parameter 'verbose' must be of type bool.")

    def test_verbose_print__raises_value_error_for_no_messages(self):
        with self.assertRaises(ValueError) as context:
            verbose_print(True)
        self.assertEqual(str(context.exception), "At least one message must be provided.")

class TestCheckAndWarnFileOverwrite(unittest.TestCase):  # mocks isfile
    @patch('os.path.isfile', return_value=True)
    def test_check_and_warn_file_overwrite__file_exists(self, mock_isfile):
        file_path = "/path/to/existing_file.txt"
        with self.assertWarns(Warning) as warning:
            warn_file_overwrite(file_path)
        self.assertIn("overwriting a file that already exists", str(warning.warning))

    @patch('os.path.isfile', return_value=False)
    def test_check_and_warn_file_overwrite__file_does_not_exist(self, mock_isfile):
        file_path = "/path/to/non_existing_file.txt"
        with self.assertRaises(AssertionError):
            with self.assertWarns(Warning):
                warn_file_overwrite(file_path)


### SUFFIX
class TestGetSuffix(unittest.TestCase):  # no mock
    def test_get_suffix__with_single_period(self):
        self.assertEqual(get_suffix("filename_v1.txt", "_"), "_v1")

    def test_get_suffix__with_no_period(self):
        self.assertEqual(get_suffix("filename_v1", "_"), "_v1")

    # Updated this test to expect a valid suffix instead of a ValueError
    def test_get_suffix__with_period_in_middle_filename(self):
        self.assertEqual(get_suffix("filename_v1.0_qa.txt", "_"), "_qa")

    def test_get_suffix__with_period_in_suffix(self):
        with self.assertRaises(ValueError):
            get_suffix("filename_v1.backup.txt", "_")

    def test_get_suffix__with_no_delimiter(self):
        self.assertIsNone(get_suffix("filename.txt", "_"))

    def test_get_suffix__with_space_in_suffix(self):
        self.assertIsNone(get_suffix("filename_v 1.txt", "_"))

    def test_get_suffix__with_no_extension(self):
        self.assertEqual(get_suffix("filename_v1", "_"), "_v1")

    def test_get_suffix__with_period_in_path(self):
        self.assertEqual(get_suffix("path.to/filename_v1.txt", "_"), "_v1")

    def test_get_suffix__with_multiple_delimiters(self):
        self.assertEqual(get_suffix("filename__v1.txt", "_"), "_v1")

    def test_get_suffix__with_delimiter_at_end(self):
        self.assertEqual(get_suffix("filename_.txt", "_"), "_")

    # Updated this test to expect a valid suffix instead of a ValueError
    def test_get_suffix__with_period_and_space_in_suffix(self):
        self.assertEqual(get_suffix("data/test file string with a extra .period_vrb.md", "_"), "_vrb")

    def test_get_suffix__with_space_in_filename(self):
        self.assertIsNone(get_suffix("data/test file string_with space.md", "_"))

    def test_get_suffix__with_suffix_containing_dash(self):
        self.assertEqual(get_suffix("data/test file string_vrb-dq.md", "_"), "_vrb-dq")

    def test_get_suffix__with_suffix_containing_at_symbol(self):
        with self.assertRaises(ValueError):
            get_suffix("data/2024-03-02_test file string_vrb@dq.md", "_")

    def test_get_suffix__with_date_in_filename(self):
        self.assertIsNone(get_suffix("data/2024-03-02_test.md", "_"))

    def test_get_suffix__with_underscore_at_end_of_filename(self):
        self.assertEqual(get_suffix("tests/test file string_", "_"), "_")

    def test_get_suffix__with_period_before_suffix_no_extension(self):
        # When extension is stripped and there's a period in the filename (like v1.2), suffix should still be found
        self.assertEqual(get_suffix("Resulting Decision Flow Chart v1.2_fixed", "_"), "_fixed")

    def test_get_suffix__with_version_number_period_no_extension(self):
        # Another case with version number period before suffix, no file extension
        self.assertEqual(get_suffix("filename_v1.0_suffix", "_"), "_suffix")

class TestSubSuffixInStr(unittest.TestCase):  # need further testing of different delimters
    def test_sub_suffix_in_str__existing_suffix(self):
        # Test replacing existing suffix
        self.assertEqual(sub_suffix_in_str("0_document file_v1.txt", "_v2"), "0_document file_v2.txt")

    def test_sub_suffix_in_str__no_existing_suffix(self):
        # Test replacing suffix when there is no existing suffix
        self.assertEqual(sub_suffix_in_str("0_document file.txt", "_v2"), "0_document file_v2.txt")

    def test_sub_suffix_in_str__no_extension(self):
        # Test with no extension
        self.assertEqual(sub_suffix_in_str("0_document file", "_v2"), "0_document file_v2")

    def test_sub_suffix_in_str__no_suffix_no_extension(self):
        # Test with no suffix and no extension, using a delimiter
        self.assertEqual(sub_suffix_in_str("0_document file", "_v2", delimiter="-"), "0_document file_v2")

    def test_sub_suffix_in_str__same_suffix(self):
        # Test with the same suffix as the substitution
        self.assertEqual(sub_suffix_in_str("2099-01-01_Test file_same.md", "_same", delimiter="_"), "2099-01-01_Test file_same.md")

class TestAddSuffixInStr(unittest.TestCase):  # no mock
    def test_add_suffix_in_str__with_extension(self):
        # Test adding suffix to file with extension
        self.assertEqual(add_suffix_in_str("document.txt", "_new"), "document_new.txt")

    def test_add_suffix_in_str__no_extension(self):
        # Test adding suffix to file without extension
        self.assertEqual(add_suffix_in_str("document", "_new"), "document_new")

    def test_add_suffix_in_str__different_delimiter(self):
        # Test adding suffix with different delimiter
        self.assertEqual(add_suffix_in_str("document.txt", "-new"), "document-new.txt")

    def test_add_suffix_in_str__same_suffix_present(self):
        # Test adding a suffix that is already present in the file name
        self.assertEqual(add_suffix_in_str("2099-01-01_Test file_same.md", "_same"), "2099-01-01_Test file_same_same.md")

class TestRemoveAllSuffixesInStr(unittest.TestCase):
    def test_remove_all_suffixes_in_str__multiple_suffixes(self):
        file_str = "2024-03-12_Title with a space_suf1_suf2.md"
        expected_result = "2024-03-12_Title with a space.md"
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

    def test_remove_all_suffixes_in_str__single_suffix(self):
        file_str = "filename_suffix.txt"
        expected_result = "filename.txt"
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

    def test_remove_all_suffixes_in_str__no_suffix(self):
        file_str = "filename.txt"
        expected_result = "filename.txt"
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

    def test_remove_all_suffixes_in_str__custom_delimiter(self):
        file_str = "filename-suffix1-suffix2.txt"
        expected_result = "filename.txt"
        self.assertEqual(remove_all_suffixes_in_str(file_str, delimiter="-"), expected_result)

    def test_remove_all_suffixes_in_str__period_start_str(self):
        file_str = ".f.txt"
        expected_result = ".f.txt"
        self.assertEqual(remove_all_suffixes_in_str(file_str, "_"), expected_result)

    def test_remove_all_suffixes_in_str__with_short_filename(self):
        file_str = "f.txt"
        expected_result = "f.txt"
        self.assertEqual(remove_all_suffixes_in_str(file_str, "_"), expected_result)

    def test_remove_all_suffixes_in_str__empty_filename(self):
        file_str = ""
        expected_result = ""
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

    def test_remove_all_suffixes_in_str__period_before_suffix_no_extension(self):
        # When there's a period in the filename (like v1.2) and no file extension, suffix should still be removed
        file_str = "Resulting Decision Flow Chart v1.2_fixed"
        expected_result = "Resulting Decision Flow Chart v1.2"
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

    def test_remove_all_suffixes_in_str__version_number_period_no_extension(self):
        # When delimiter is after the period, period is part of filename and suffix is removed
        # For filename_v1.0_suffix: _suffix is after .0 so it's removed, then _v1 is before .0 so it's also removed
        file_str = "filename_v1.0_suffix"
        expected_result = "filename"
        self.assertEqual(remove_all_suffixes_in_str(file_str), expected_result)

class TestMOCKHandleOverwritePrompt(unittest.TestCase):  # mocks rename, remove, input and user functions verbose
    @patch('os.rename')
    @patch('os.remove')
    @patch('core.fileops.verbose_print')
    @patch('os.path.isfile')
    @patch('builtins.input', side_effect=['y'])
    def testmock_handle_overwrite_prompt__overwrite_yes(self, mock_input, mock_isfile, mock_verbose_print, mock_remove, mock_rename):
        file_path = "/path/to/original_file.txt"
        file_path_opfunc = "/path/to/new_file.txt"
        mock_isfile.return_value = True

        result = handle_overwrite_prompt(file_path, file_path_opfunc)

        self.assertEqual(result, file_path)
        mock_remove.assert_called_once_with(file_path)
        mock_rename.assert_called_once_with(file_path_opfunc, file_path)
        mock_verbose_print.assert_called_once_with(True, "File operation with overwrite=prompt+yes - overwrite original file.")

    @patch('os.rename')
    @patch('os.remove')
    @patch('core.fileops.verbose_print')
    @patch('os.path.isfile')
    @patch('builtins.input', side_effect=['n'])
    def testmock_handle_overwrite_prompt__overwrite_no(self, mock_input, mock_isfile, mock_verbose_print, mock_remove, mock_rename):
        file_path = "/path/to/original_file.txt"
        file_path_opfunc = "/path/to/new_file.txt"
        mock_isfile.return_value = True

        result = handle_overwrite_prompt(file_path, file_path_opfunc)

        self.assertEqual(result, file_path_opfunc)
        mock_remove.assert_not_called()
        mock_rename.assert_not_called()
        mock_verbose_print.assert_called_once_with(True, "File operation with overwrite=prompt+no - keep original file and new file.")

    @patch('os.path.basename', return_value="original_file.txt")
    @patch('core.fileops.sub_suffix_in_str', return_value="/path/to/original_file_newsuffix.txt")
    @patch('core.fileops.get_suffix', return_value="_newsuffix")
    @patch('os.rename')
    @patch('core.fileops.verbose_print')
    @patch('os.path.isfile')
    @patch('builtins.input', side_effect=['s'])
    def testmock_handle_overwrite_prompt__overwrite_sub(self, mock_input, mock_isfile, mock_verbose_print, mock_rename, mock_get_suffix, mock_sub_suffix_in_str, mock_basename):
        file_path = "/path/to/original_file.txt"
        file_path_opfunc = "/path/to/original_file_newsuffix.txt"
        expected_substituted_path = "/path/to/original_file_newsuffix.txt"
        mock_isfile.return_value = True

        result = handle_overwrite_prompt(file_path, file_path_opfunc)

        self.assertEqual(result, expected_substituted_path)
        mock_rename.assert_called_once_with(file_path_opfunc, expected_substituted_path)
        mock_verbose_print.assert_called_once_with(True, "File operation with overwrite=prompt+sub - keep original file and new file with substituted suffix.")

    @patch('os.rename')
    @patch('os.remove')
    @patch('core.fileops.verbose_print')
    @patch('os.path.isfile')
    @patch('builtins.input', side_effect=['invalid', 'y'])
    def testmock_handle_overwrite_prompt__invalid_input_then_overwrite(self, mock_input, mock_isfile, mock_verbose_print, mock_remove, mock_rename):
        file_path = "/path/to/original_file.txt"
        file_path_opfunc = "/path/to/new_file.txt"
        mock_isfile.return_value = True

        result = handle_overwrite_prompt(file_path, file_path_opfunc)

        self.assertEqual(result, file_path)
        mock_remove.assert_called_once_with(file_path)
        mock_rename.assert_called_once_with(file_path_opfunc, file_path)
        mock_verbose_print.assert_called_once_with(True, "File operation with overwrite=prompt+yes - overwrite original file.")

class TestHandleOverwritePrompt(unittest.TestCase):  # mocks rename, remove, input
    def setUp(self):
        # Create temporary files for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "Test file_orig.txt")
        self.file_path_opfunc = os.path.join(self.temp_dir.name, "Test file_orig_new.txt")
        with open(self.file_path, 'w') as f:
            f.write("Original file content")
        with open(self.file_path_opfunc, 'w') as f:
            f.write("Modified file content")

    def tearDown(self):
        # Clean up temporary files
        self.temp_dir.cleanup()

    @patch('os.rename')
    @patch('os.remove')
    @patch('builtins.input', side_effect=['y'])
    def test_handle_overwrite_prompt__overwrite_yes(self, mock_input, mock_remove, mock_rename):
        result = handle_overwrite_prompt(self.file_path, self.file_path_opfunc)
        self.assertEqual(result, self.file_path)
        mock_remove.assert_called_once_with(self.file_path)
        mock_rename.assert_called_once_with(self.file_path_opfunc, self.file_path)

    @patch('os.rename')
    @patch('os.remove')
    @patch('builtins.input', side_effect=['n'])
    def test_handle_overwrite_prompt__overwrite_no(self, mock_input, mock_remove, mock_rename):
        result = handle_overwrite_prompt(self.file_path, self.file_path_opfunc)
        self.assertEqual(result, self.file_path_opfunc)
        mock_remove.assert_not_called()
        mock_rename.assert_not_called()

    @patch('os.rename')
    @patch('builtins.input', side_effect=['s'])
    def test_handle_overwrite_prompt__overwrite_sub(self, mock_input, mock_rename):
        expected_substituted_path = os.path.join(self.temp_dir.name, "Test file_new.txt")
        result = handle_overwrite_prompt(self.file_path, self.file_path_opfunc)
        self.assertEqual(result, expected_substituted_path)
        mock_rename.assert_called_once_with(self.file_path_opfunc, expected_substituted_path)

    @patch('os.rename')
    @patch('os.remove')
    @patch('builtins.input', side_effect=['invalid', 'y'])
    def test_handle_overwrite_prompt__invalid_input_then_overwrite(self, mock_input, mock_remove, mock_rename):
        result = handle_overwrite_prompt(self.file_path, self.file_path_opfunc)
        self.assertEqual(result, self.file_path)
        mock_remove.assert_called_once_with(self.file_path)
        mock_rename.assert_called_once_with(self.file_path_opfunc, self.file_path)


###FOLDER
class TestGetFilesInFolder(unittest.TestCase):  # no mock (except input)
    def setUp(self):
        # Create a temporary directory with files and a subfolder
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file1 = os.path.join(self.temp_dir.name, "2000-01-01_Test file 1_dgwhspm.json")
        self.file2 = os.path.join(self.temp_dir.name, "2000-01-01_Test file 2_dgwhspm.md")
        self.file3 = os.path.join(self.temp_dir.name, "2099-01-01_Test file 3_flaws.md")
        self.subfolder = os.path.join(self.temp_dir.name, "my_subfolder")
        self.subfolder_file1 = os.path.join(self.subfolder, "2000-01-01_Test file 4_dgwhspm.md")
        self.subfolder_file2 = os.path.join(self.subfolder, "2099-01-01_Test file 5_flaws.md")
        os.mkdir(self.subfolder)
        for file in [self.file1, self.file2, self.file3, self.subfolder_file1, self.subfolder_file2]:
            with open(file, 'w') as f:
                f.write("Test content")

    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    def test_get_files_in_folder__all_files(self):
        result = get_files_in_folder(self.temp_dir.name)
        self.assertEqual(set(result), {self.file1, self.file2, self.file3})

    def test_get_files_in_folder__include_subfolders(self):
        result = get_files_in_folder(self.temp_dir.name, include_subfolders=True)
        self.assertEqual(set(result), {self.file1, self.file2, self.file3, self.subfolder_file1, self.subfolder_file2})

    def test_get_files_in_folder__suffixpat_include(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_include='_dgwhspm')
        self.assertEqual(set(result), {self.file1, self.file2})

    def test_get_files_in_folder__suffixpat_exclude(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_exclude='_flaws')
        self.assertEqual(set(result), {self.file1, self.file2})

    def test_get_files_in_folder__suffixpat_include_no_match(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_include='_prepqa', include_subfolders=True)
        self.assertEqual(result, [])

    def test_get_files_in_folder__nonexistent_folder(self):
        with self.assertRaises(ValueError):
            get_files_in_folder(os.path.join(self.temp_dir.name, "nonexistent_folder"))

    def test_get_files_in_folder__both_suffixpat_include_and_exclude(self):
        with self.assertRaises(ValueError):
            get_files_in_folder(self.temp_dir.name, suffixpat_include='_qatest', suffixpat_exclude='_prepqa')

    def test_get_files_in_folder__suffixpat_include_with_dot(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_include='.md')
        self.assertEqual(set(result), {self.file2, self.file3})

    def test_get_files_in_folder__suffixpat_exclude_with_dot(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_exclude='.json')
        self.assertEqual(set(result), {self.file2, self.file3})

    def test_get_files_in_folder__suffixpat_include_with_dot_and_subfolders(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_include='.md', include_subfolders=True)
        self.assertEqual(set(result), {self.file2, self.file3, self.subfolder_file1, self.subfolder_file2})

    def test_get_files_in_folder__suffixpat_exclude_with_dot_and_subfolders(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_exclude='.md', include_subfolders=True)
        self.assertEqual(set(result), {self.file1})

    def test_get_files_in_folder__suffixpat_include_json(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_include='.json')
        self.assertEqual(set(result), {self.file1})

    def test_get_files_in_folder__suffixpat_exclude_json_with_subfolders(self):
        result = get_files_in_folder(self.temp_dir.name, suffixpat_exclude='.json', include_subfolders=True)
        self.assertEqual(set(result), {self.file2, self.file3, self.subfolder_file1, self.subfolder_file2})

def mock_function(file_path, *args, **kwargs):
    return f"Processed {os.path.basename(file_path)}"

class TestApplyToFolder(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory with files and a subfolder
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file1 = os.path.join(self.temp_dir.name, "file1.txt")
        self.file2 = os.path.join(self.temp_dir.name, "file2_prepqa.txt")
        self.subfolder = os.path.join(self.temp_dir.name, "subfolder")
        self.subfolder_file = os.path.join(self.subfolder, "file3.txt")
        os.mkdir(self.subfolder)
        with open(self.file1, 'w') as f:
            f.write("File 1 content")
        with open(self.file2, 'w') as f:
            f.write("File 2 content")
        with open(self.subfolder_file, 'w') as f:
            f.write("Subfolder file content")

    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    def test_apply_to_folder__no_suffix(self):
        results = apply_to_folder(mock_function, self.temp_dir.name)
        expected_results = {
            self.file1: "Processed file1.txt",
            self.file2: "Processed file2_prepqa.txt"
        }
        self.assertEqual(results, expected_results)

    def test_apply_to_folder__suffix_include(self):
        results = apply_to_folder(mock_function, self.temp_dir.name, suffixpat_include='_prepqa')
        expected_results = {
            self.file2: "Processed file2_prepqa.txt"
        }
        self.assertEqual(results, expected_results)

    def test_apply_to_folder__suffix_exclude(self):
        results = apply_to_folder(mock_function, self.temp_dir.name, suffixpat_exclude='_prepqa')
        expected_results = {
            self.file1: "Processed file1.txt"
        }
        self.assertEqual(results, expected_results)

    def test_apply_to_folder__include_subfolders(self):
        results = apply_to_folder(mock_function, self.temp_dir.name, include_subfolders=True)
        expected_results = {
            self.file1: "Processed file1.txt",
            self.file2: "Processed file2_prepqa.txt",
            self.subfolder_file: "Processed file3.txt"
        }
        self.assertEqual(results, expected_results)

    def test_apply_to_folder__suffix_include_and_exclude(self):
        with self.assertRaises(ValueError):
            apply_to_folder(mock_function, self.temp_dir.name, suffixpat_include='_prepqa', suffixpat_exclude='_prepqa')


### READ WRITE
class TestReadCompleteText(unittest.TestCase):
    @patch('os.path.isfile', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="File content")
    def test_read_complete_text__returns_file_content(self, mock_file, mock_isfile):
        file_path = "/path/to/file.txt"
        self.assertEqual(read_complete_text(file_path), "File content")

    @patch('os.path.isfile', return_value=False)
    def test_read_complete_text__raises_value_error_for_nonexistent_path(self, mock_isfile):
        file_path = "/nonexistent/path/to/file.txt"
        with self.assertRaises(ValueError):
            read_complete_text(file_path)

def test_read_metadata_and_content__format2(self, mock_isfile):
    content = "METADATA\nTitle: Test\nAuthor: John\nCONTENT\nThis is the main content."
    mock_open_func = mock_open(read_data=content)
    with patch('builtins.open', mock_open_func):
        metadata, content = read_metadata_and_content(self.file_path)
    
    # Updated to include METADATA header
    self.assertEqual(metadata, "METADATA\nTitle: Test\nAuthor: John")
    self.assertEqual(content, "CONTENT\nThis is the main content.")

def test_read_metadata_and_content__integration_format2(self):
    content = "METADATA\nTitle: Test\nAuthor: John\nCONTENT\nThis is the main content."
    with open(self.file_path, 'w') as f:
        f.write(content)
    
    metadata, content = read_metadata_and_content(self.file_path)
    
    # Updated to include METADATA header
    self.assertEqual(metadata, "METADATA\nTitle: Test\nAuthor: John")
    self.assertEqual(content, "CONTENT\nThis is the main content.")

def test_read_file_flex__format2(self, mock_isfile):
    content = "METADATA\nTitle: Test\nAuthor: John\nCONTENT\nThis is the main content."
    mock_open_func = mock_open(read_data=content)
    with patch('builtins.open', mock_open_func):
        metadata, content = read_file_flex(self.file_path)
    
    # Updated to include METADATA header
    self.assertEqual(metadata, "METADATA\nTitle: Test\nAuthor: John")
    self.assertEqual(content, "CONTENT\nThis is the main content.")

def test_read_file_flex__integration_format2(self):
    content = "METADATA\nTitle: Test\nAuthor: John\nCONTENT\nThis is the main content."
    with open(self.file_path, 'w') as f:
        f.write(content)
    
    metadata, content = read_file_flex(self.file_path)
    
    # Updated to include METADATA header
    self.assertEqual(metadata, "METADATA\nTitle: Test\nAuthor: John")
    self.assertEqual(content, "CONTENT\nThis is the main content.")

class TestManageFileOverwrite(unittest.TestCase):
    def setUp(self):
        self.original_path = "test_orig.md"
        self.suffix_new = "_new"
        self.content = "Test content"

    def tearDown(self):
        for file in [self.original_path, "test_orig_new.md", "test_new.md"]:
            if os.path.exists(file):
                os.remove(file)

    def create_test_files(self):
        with open(self.original_path, 'w') as f:
            f.write(self.content)
        with open(add_suffix_in_str(self.original_path, self.suffix_new), 'w') as f:
            f.write(self.content)

    def test_manage_file_overwrite__no(self):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "no")
        self.assertEqual(result, add_suffix_in_str(self.original_path, self.suffix_new))
        self.assertTrue(os.path.exists(self.original_path))
        self.assertTrue(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    def test_manage_file_overwrite__no_sub(self):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "no-sub")
        expected_path = "test_new.md"
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.exists(self.original_path))
        self.assertTrue(os.path.exists(expected_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    def test_manage_file_overwrite__replace(self):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "replace")
        self.assertEqual(result, self.original_path)
        self.assertTrue(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    def test_manage_file_overwrite__replace_sub(self):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "replace-sub")
        expected_path = "test_new.md"
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.exists(expected_path))
        self.assertFalse(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    def test_manage_file_overwrite__yes(self):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "yes")
        self.assertEqual(result, self.original_path)
        self.assertTrue(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    @patch('core.fileops.handle_overwrite_prompt')
    def test_manage_file_overwrite__prompt(self, mock_prompt):
        self.create_test_files()
        mock_prompt.return_value = self.original_path
        result = manage_file_overwrite(self.original_path, self.suffix_new, "prompt")
        self.assertEqual(result, self.original_path)
        mock_prompt.assert_called_once_with(self.original_path, add_suffix_in_str(self.original_path, self.suffix_new), False)

    def test_manage_file_overwrite__invalid_mode(self):
        with self.assertRaises(ValueError) as context:
            manage_file_overwrite(self.original_path, self.suffix_new, "invalid")
        self.assertEqual(str(context.exception), "Invalid overwrite mode: invalid")

    @patch('core.fileops.verbose_print')
    def test_manage_file_overwrite__verbose_output(self, mock_print):
        self.create_test_files()
        manage_file_overwrite(self.original_path, self.suffix_new, "no", verbose=True)
        mock_print.assert_called_once_with(True, "manage_file_overwrite in mode: 'no' - Keeping both original and new files.")

    @patch('os.remove')
    @patch('os.rename')
    @patch('os.path.exists')
    def test_manage_file_overwrite__file_operations(self, mock_exists, mock_rename, mock_remove):
        mock_exists.return_value = True  # Simulate that the original file exists
        manage_file_overwrite(self.original_path, self.suffix_new, "replace")
        mock_remove.assert_called_once_with(self.original_path)
        mock_rename.assert_called_once_with(add_suffix_in_str(self.original_path, self.suffix_new), self.original_path)

    @patch('core.fileops.sub_suffix_in_str')
    def test_manage_file_overwrite__suffix_functions_called(self, mock_sub_suffix):
        mock_sub_suffix.return_value = "test_new.md"
        self.create_test_files()
        manage_file_overwrite(self.original_path, self.suffix_new, "no-sub")
        mock_sub_suffix.assert_called_once_with(self.original_path, self.suffix_new)

    @patch('builtins.input', side_effect=['y'])
    def test_manage_file_overwrite__prompt_yes(self, mock_input):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "prompt")
        self.assertEqual(result, self.original_path)
        self.assertTrue(os.path.exists(self.original_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    @patch('builtins.input', side_effect=['n'])
    def test_manage_file_overwrite__prompt_no(self, mock_input):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "prompt")
        self.assertEqual(result, add_suffix_in_str(self.original_path, self.suffix_new))
        self.assertTrue(os.path.exists(self.original_path))
        self.assertTrue(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

    @patch('builtins.input', side_effect=['s'])
    def test_manage_file_overwrite__prompt_sub(self, mock_input):
        self.create_test_files()
        result = manage_file_overwrite(self.original_path, self.suffix_new, "prompt")
        expected_path = "test_new.md"
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.exists(self.original_path))
        self.assertTrue(os.path.exists(expected_path))
        self.assertFalse(os.path.exists(add_suffix_in_str(self.original_path, self.suffix_new)))

class TestWriteCompleteText(unittest.TestCase):
    def setUp(self):
        self.original_path = "test_orig.txt"
        self.new_path = "test_orig_new.txt"
        self.complete_text = "This is the complete text."
        self.suffix_new = "_new"

    def tearDown(self):
        for file in [self.original_path, self.new_path]:
            if os.path.exists(file):
                os.remove(file)

    @patch('core.fileops.add_suffix_in_str')
    @patch('core.fileops.manage_file_overwrite')
    def test_write_complete_text__basic_functionality(self, mock_manage, mock_add_suffix):
        mock_add_suffix.return_value = self.new_path
        mock_manage.return_value = self.new_path

        result = write_complete_text(self.original_path, self.complete_text, self.suffix_new)

        mock_add_suffix.assert_called_once_with(self.original_path, self.suffix_new)
        mock_manage.assert_called_once_with(self.original_path, self.suffix_new, 'no', False)
        self.assertEqual(result, self.new_path)

        with open(self.new_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, self.complete_text)

    @patch('core.fileops.add_suffix_in_str')
    @patch('core.fileops.manage_file_overwrite')
    @patch('core.fileops.warn_file_overwrite')
    def test_write_complete_text__verbose_file_exists(self, mock_warn, mock_manage, mock_add_suffix):
        mock_add_suffix.return_value = self.new_path
        mock_manage.return_value = self.new_path

        with patch('builtins.print') as mock_print, patch('os.path.isfile', return_value=True):
            write_complete_text(self.original_path, self.complete_text, self.suffix_new, verbose=True)

        mock_print.assert_called_once_with("BEFORE OVERWRITE write_complete_text new_file_path does exist.")
        mock_warn.assert_called_once_with(self.new_path)

    @patch('core.fileops.add_suffix_in_str')
    @patch('core.fileops.manage_file_overwrite')
    def test_write_complete_text__verbose_file_not_exists(self, mock_manage, mock_add_suffix):
        mock_add_suffix.return_value = self.new_path
        mock_manage.return_value = self.new_path

        with patch('builtins.print') as mock_print, patch('os.path.isfile', return_value=False):
            write_complete_text(self.original_path, self.complete_text, self.suffix_new, verbose=True)

        mock_print.assert_called_once_with("BEFORE OVERWRITE write_complete_text new_file_path does NOT exist (note this file may be an intermediate file that is deleted or renamed by manage_file_overwrite).")

    @patch('core.fileops.add_suffix_in_str')
    @patch('core.fileops.manage_file_overwrite')
    def test_write_complete_text__different_overwrite_modes(self, mock_manage, mock_add_suffix):
        mock_add_suffix.return_value = self.new_path
        mock_manage.return_value = self.original_path  # Simulating 'yes' or 'replace' mode

        result = write_complete_text(self.original_path, self.complete_text, self.suffix_new, overwrite='yes')

        mock_manage.assert_called_once_with(self.original_path, self.suffix_new, 'yes', False)
        self.assertEqual(result, self.original_path)

    @patch('core.fileops.add_suffix_in_str')
    @patch('core.fileops.manage_file_overwrite')
    def test_write_complete_text__file_write_error(self, mock_manage, mock_add_suffix):
        mock_add_suffix.return_value = self.new_path
        
        with patch('builtins.open', side_effect=IOError("Unable to write file")):
            with self.assertRaises(IOError):
                write_complete_text(self.original_path, self.complete_text, self.suffix_new)

        mock_manage.assert_not_called()

class TestWriteMetadataAndContent(unittest.TestCase):
    def setUp(self):
        self.file_path = "test_orig.txt"
        self.metadata = "## metadata\nTitle: Test\nAuthor: John Doe"
        self.content = "## content\nThis is the main content."
        self.suffix_new = "_new"
        self.complete_text = f"{self.metadata}\n\n\n{self.content}\n"

    def tearDown(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__basic_functionality(self, mock_write_complete):
        mock_write_complete.return_value = "test_orig_new.txt"

        result = write_metadata_and_content(self.file_path, self.metadata, self.content, self.suffix_new)

        mock_write_complete.assert_called_once_with(self.file_path, self.complete_text, self.suffix_new, 'no', False)
        self.assertEqual(result, "test_orig_new.txt")

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__custom_overwrite(self, mock_write_complete):
        mock_write_complete.return_value = "test_orig.txt"

        result = write_metadata_and_content(self.file_path, self.metadata, self.content, self.suffix_new, overwrite='yes')

        mock_write_complete.assert_called_once_with(self.file_path, self.complete_text, self.suffix_new, 'yes', False)
        self.assertEqual(result, "test_orig.txt")

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__verbose_mode(self, mock_write_complete):
        mock_write_complete.return_value = "test_orig_new.txt"

        result = write_metadata_and_content(self.file_path, self.metadata, self.content, self.suffix_new, verbose=True)

        mock_write_complete.assert_called_once_with(self.file_path, self.complete_text, self.suffix_new, 'no', True)
        self.assertEqual(result, "test_orig_new.txt")

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__alternative_format(self, mock_write_complete):
        metadata = "METADATA\nTitle: Test\nAuthor: John Doe"
        content = "CONTENT\nThis is the main content."
        complete_text = f"{metadata}\n\n\n{content}\n"

        result = write_metadata_and_content(self.file_path, metadata, content, self.suffix_new)

        mock_write_complete.assert_called_once_with(self.file_path, complete_text, self.suffix_new, 'no', False)

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__empty_metadata(self, mock_write_complete):
        metadata = ""
        complete_text = f"\n\n\n{self.content}\n"

        result = write_metadata_and_content(self.file_path, metadata, self.content, self.suffix_new)

        mock_write_complete.assert_called_once_with(self.file_path, complete_text, self.suffix_new, 'no', False)

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__empty_content(self, mock_write_complete):
        content = ""
        complete_text = f"{self.metadata}\n\n\n\n"

        result = write_metadata_and_content(self.file_path, self.metadata, content, self.suffix_new)

        mock_write_complete.assert_called_once_with(self.file_path, complete_text, self.suffix_new, 'no', False)

    @patch('core.fileops.write_complete_text', side_effect=IOError("Unable to write file"))
    def test_write_metadata_and_content__write_error(self, mock_write_complete):
        with self.assertRaises(IOError):
            write_metadata_and_content(self.file_path, self.metadata, self.content, self.suffix_new)

    def test_write_metadata_and_content__integration(self):
        result = write_metadata_and_content(self.file_path, self.metadata, self.content, self.suffix_new)
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as f:
            content = f.read()
        self.assertEqual(content, self.complete_text)

        os.remove(result)  # Clean up the created file

    @patch('core.fileops.write_complete_text')
    def test_write_metadata_and_content__format2_conversion(self, mock_write_complete):
        # Test that when metadata is in Format 2 (METADATA), content is converted to Format 2 (CONTENT)
        metadata = "METADATA\nTitle: Test\nAuthor: John Doe"
        content = "## content\nThis is the main content."  # Format 1 content
        expected_content = "CONTENT\nThis is the main content."  # Should be converted to Format 2
        expected_complete_text = f"{metadata}\n\n\n{expected_content}\n"

        result = write_metadata_and_content(self.file_path, metadata, content, self.suffix_new)

        mock_write_complete.assert_called_once_with(self.file_path, expected_complete_text, self.suffix_new, 'no', False)
        self.assertEqual(result, mock_write_complete.return_value)

### MISC
class TestRenameFile(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directory after the test
        shutil.rmtree(self.temp_dir)

    def test_rename_file__successful_rename(self):
        # Create a temporary file
        temp_file = os.path.join(self.temp_dir, "tempfile.txt")
        with open(temp_file, "w") as f:
            f.write("Hello world")

        # Test renaming the file
        new_base = "newtempfile"
        expected_path = os.path.join(self.temp_dir, "newtempfile.txt")
        result = rename_file(temp_file, new_base)
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.isfile(expected_path))

    def test_rename_file__file_is_invalid(self):
        # Pass an invalid or non-existent file path
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        with self.assertRaises(ValueError):
            rename_file(non_existent_file, "newfile")

class TestDeleteFile(unittest.TestCase):
    def setUp(self):
        # Setup method to create a test file before each test case
        self.test_filename = 'test_file.txt'
        with open(self.test_filename, 'w') as f:
            f.write('Test content')

    def tearDown(self):
        # Teardown method to remove test file if it still exists after a test case
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_delete_file__file_deleted_successfully(self):
        # Test that a file is successfully deleted
        result = delete_file(self.test_filename)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.test_filename))

    def test_delete_file__file_does_not_exist(self):
        # Test that the function handles the case where the file does not exist
        os.remove(self.test_filename)  # Delete the file to simulate the file not existing
        result = delete_file(self.test_filename)
        self.assertIsInstance(result, OSError)

class TestDeleteFilesWithSuffix(unittest.TestCase):
    def setUp(self):
        # Setup method to create a test directory with files before each test case
        self.temp_dir = 'test_folder'
        os.mkdir(self.temp_dir)
        self.file1 = os.path.join(self.temp_dir, 'file1.txt')
        self.file2 = os.path.join(self.temp_dir, 'file2_suffix.txt')
        with open(self.file1, 'w') as f:
            f.write('File 1 content')
        with open(self.file2, 'w') as f:
            f.write('File 2 content')

    def tearDown(self):
        # Teardown method to remove test directory and files after each test case
        if os.path.exists(self.file1):
            os.remove(self.file1)
        if os.path.exists(self.file2):
            os.remove(self.file2)
        os.rmdir(self.temp_dir)

    def test_delete_files_with_suffix__files_deleted(self):
        # Test that files with the specified suffix are deleted from the folder
        suffix_include = '_suffix'
        deleted_files = delete_files_with_suffix(self.temp_dir, suffix_include)
        self.assertTrue(os.path.exists(self.file1))
        self.assertFalse(os.path.exists(self.file2))
        self.assertIn(self.file2, deleted_files)

    def test_delete_files_with_suffix__no_files_deleted(self):
        # Test that no files are deleted if no files match the specified suffix
        suffix_include = '_nonexistent_suffix.txt'
        deleted_files = delete_files_with_suffix(self.temp_dir, suffix_include)
        self.assertTrue(os.path.exists(self.file1))
        self.assertTrue(os.path.exists(self.file2))
        self.assertEqual(len(deleted_files), 0)

class TestMoveFile(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directory after each test
        shutil.rmtree(self.temp_dir)

    def test_move_file__file_not_exists(self):
        # Test the error condition where the source file does not exist
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        destination_folder = os.path.join(self.temp_dir, "dest")
        with self.assertRaises(ValueError):
            move_file(non_existent_file, destination_folder)

    def test_move_file__destination_folder_not_exists(self):
        # Test the condition where the destination folder does not exist (it should create it)
        source_file_path = os.path.join(self.temp_dir, "source.txt")
        with open(source_file_path, "w") as f:
            f.write("This is a test file.")

        new_destination_folder = os.path.join(self.temp_dir, "new_dest")
        new_file_path = move_file(source_file_path, new_destination_folder)
        self.assertTrue(os.path.exists(new_file_path))
        self.assertTrue(os.path.isdir(new_destination_folder))

    def test_move_file__successful_move(self):
        # Test successful file move
        source_file_path = os.path.join(self.temp_dir, "source.txt")
        with open(source_file_path, "w") as f:
            f.write("This is a test file.")

        destination_folder = os.path.join(self.temp_dir, "dest")
        os.mkdir(destination_folder)
        new_file_path = move_file(source_file_path, destination_folder)
        self.assertTrue(os.path.exists(new_file_path))
        self.assertFalse(os.path.exists(source_file_path))

class TestTuneTitle(unittest.TestCase):
    def test_tune_title__alphanumeric(self):
        self.assertEqual(tune_title('Title123'), 'Title123')

    def test_tune_title__spaces(self):
        self.assertEqual(tune_title('Title With Spaces'), 'Title With Spaces')

    def test_tune_title__allowed_special_characters(self):
        self.assertEqual(tune_title('Title-With-Dashes(And)Parentheses.Period'), 'Title-With-Dashes(And)Parentheses.Period')

    def test_tune_title__disallowed_special_characters(self):
        self.assertEqual(tune_title('Title!@#$%^&*+=With{}[]Special|\\:;"\'<>,?/Characters'), 'TitleWithSpecialCharacters')

    def test_tune_title__mix_allowed_disallowed_characters(self):
        self.assertEqual(tune_title('Title-123(With)Special_Characters!@#'), 'Title-123(With)Special_Characters')

    def test_tune_title__leading_trailing_special_characters(self):
        self.assertEqual(tune_title('!Title@'), 'Title')

    def test_tune_title__only_special_characters(self):
        self.assertEqual(tune_title('!@#$%^&*'), '')  # exclude parantheses because they are allowed

    def test_tune_title__path_separators(self):
        self.assertEqual(tune_title('Title/With\\Path|Separators:'), 'TitleWithPathSeparators')

    def test_tune_title__unicode_characters(self):
        self.assertEqual(tune_title('Título Con Caracteres Españolesñá'), 'Título Con Caracteres Españolesñá')

class TestCreateFullPath(unittest.TestCase):
    def test_create_full_path__empty_title_or_path(self):
        self.assertEqual(create_full_path('', '_xyz.md', 'data/audio_inbox'), 'data/audio_inbox/_xyz.md')

    def test_create_full_path__default_folder_only(self):
        self.assertEqual(create_full_path('Lost Lecture', '_xyz.md', 'data/audio_inbox'), 'data/audio_inbox/Lost Lecture_xyz.md')

    def test_create_full_path__with_existing_extension(self):
        self.assertEqual(create_full_path('Lost Lecture_blah.txt', '_xyz.md', 'data/audio_inbox'), 'data/audio_inbox/Lost Lecture_blah_xyz.md')

    def test_create_full_path__absolute_path(self):
        self.assertEqual(create_full_path('/absolute/path/Lost Lecture', '_xyz.md', 'data/audio_inbox'), '/absolute/path/Lost Lecture_xyz.md')

    def test_create_full_path__relative_path(self):
        self.assertEqual(create_full_path('relative/path/Lost Lecture', '_xyz.md', 'data/audio_inbox'), 'relative/path/Lost Lecture_xyz.md')

    def test_create_full_path__path_with_special_characters(self):
        # exclude underscore and parantheses because these are allowed in filenames
        self.assertEqual(create_full_path('Special!@#$%^&*+= Lecture', '_xyz.md', 'data/audio_inbox'), 'data/audio_inbox/Special Lecture_xyz.md')

    def test_create_full_path__path_with_spaces(self):
        self.assertEqual(create_full_path('Lost Lecture With Spaces', '_xyz.md', 'data/audio_inbox'), 'data/audio_inbox/Lost Lecture With Spaces_xyz.md')

    def test_create_full_path__path_with_dot_in_directory_name(self):
        self.assertEqual(create_full_path('data.audio.inbox/Lost Lecture', '_xyz.md', 'data/audio_inbox'), 'data.audio.inbox/Lost Lecture_xyz.md')

    def test_create_full_path__path_with_existing_extension(self):
        # Test creating a full path with an existing extension in the file title or path
        self.assertEqual(create_full_path('tests/2099-01-01_Test file with link.md', '_xyz.md'), 'tests/2099-01-01_Test file with link_xyz.md')

    def test_create_full_path__invalid_directory(self):
        # Test creating a full path with an invalid directory in the file title or path
        with self.assertRaises(ValueError):
            create_full_path('2099-01-01_Test file with link.md', '_xyz.md')

class TestFindFileInFolders(unittest.TestCase):
    def setUp(self):
        # Setup temporary folders and a file for the test
        self.temp_folder1 = tempfile.mkdtemp()
        self.temp_folder2 = tempfile.mkdtemp()
        self.file_name = "testfile.txt"
        self.file_path = os.path.join(self.temp_folder1, self.file_name)
        with open(self.file_path, 'w') as f:
            f.write('Test content')

    def tearDown(self):
        # Clean up by removing temporary folders
        shutil.rmtree(self.temp_folder1)
        shutil.rmtree(self.temp_folder2)

    def test_file_found_in_folder(self):
        # Test finding the file in the folders
        found_path = find_file_in_folders(self.file_name, [self.temp_folder1, self.temp_folder2])
        self.assertEqual(found_path, self.file_path)

    def test_file_not_found_in_folder(self):
        # Test not finding the file when it's not in the folders
        found_path = find_file_in_folders("nonexistent.txt", [self.temp_folder1, self.temp_folder2])
        self.assertIsNone(found_path)

    def test_file_already_exists(self):
        # Test the warning when the file already exists at the given path
        with self.assertWarns(Warning):
            found_path = find_file_in_folders(self.file_path, [self.temp_folder1, self.temp_folder2])
        self.assertEqual(found_path, self.file_path)

class TestCopyFileAndAppendSuffix(unittest.TestCase):
    def setUp(self):
        # Setup method to create a test file before each test case
        self.test_filename = 'test_file.txt'
        with open(self.test_filename, 'w') as f:
            f.write('Test content')

    def tearDown(self):
        # Teardown method to remove test files after each test case
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)
        new_filename = self.test_filename.replace('.txt', '_backup.txt')
        if os.path.exists(new_filename):
            os.remove(new_filename)

    def test_copy_file_and_append_suffix__file_copied(self):
        # Test that a new file is created with the specified suffix
        new_filename = copy_file_and_append_suffix(self.test_filename, '_backup')
        self.assertTrue(os.path.exists(new_filename))
        with open(new_filename, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'Test content')

    def test_copy_file_and_append_suffix__file_does_not_exist(self):
        # Test that an error is raised if the original file does not exist
        with self.assertRaises(ValueError):
            copy_file_and_append_suffix('nonexistent_file.txt', '_backup')

class TestSubSuffixInFile(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to hold the test files
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove all created test files and directory after each test
        for filename in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, filename)
            os.unlink(file_path)
        os.rmdir(self.test_dir)

    def test__valid_substitution_with_suffix(self):
        # Test substitution where the original file has a valid suffix
        file_path = os.path.join(self.test_dir, "example_file_oldSuffix.txt")
        with open(file_path, "w") as file:
            file.write("Hello, world!")
        new_suffix = "_newSuffix"
        expected_file_path = os.path.join(self.test_dir, "example_file_newSuffix.txt")

        result = sub_suffix_in_file(file_path, new_suffix)

        self.assertEqual(result, expected_file_path)
        self.assertTrue(os.path.isfile(expected_file_path))

    def test__error_on_nonexistent_file(self):
        # Test behavior when the file does not exist
        file_path = os.path.join(self.test_dir, "nonexistent_file.txt")
        new_suffix = "_newSuffix"

        with self.assertRaises(ValueError) as context:
            sub_suffix_in_file(file_path, new_suffix)

    def test__remove_suffix_when_empty_string_passed(self):
        # Test removing the suffix by passing an empty string as the new suffix
        file_path = os.path.join(self.test_dir, "example_file_oldSuffix.txt")
        with open(file_path, "w") as file:
            file.write("Testing suffix removal")
        new_suffix = ""
        expected_file_path = os.path.join(self.test_dir, "example_file.txt")

        result = sub_suffix_in_file(file_path, new_suffix)

        self.assertEqual(result, expected_file_path)
        self.assertTrue(os.path.isfile(expected_file_path))

    def test__handle_invalid_suffix_characters(self):
        # Test handling of invalid characters in the suffix to ensure they're handled gracefully
        file_path = os.path.join(self.test_dir, "example_file_invalid_suffix?.txt")
        with open(file_path, "w") as file:
            file.write("Testing invalid characters")
        new_suffix = "_newSuffix"

        with self.assertRaises(ValueError) as context:
            sub_suffix_in_file(file_path, new_suffix)

        self.assertIn("The extracted suffix contains invalid characters", str(context.exception))

class TestCountSuffixesInFolder(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        # Setup to capture print statements
        # Create StringIO object
        self.capturedOutput = StringIO()
        # and redirect stdout.
        sys.stdout = self.capturedOutput

    def tearDown(self):
        # Remove all files in the temporary directory
        for filename in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, filename)
            os.unlink(file_path)
        # Remove the temporary directory after all files have been deleted
        os.rmdir(self.test_dir)
        # Reset stdout
        # Reset redirect.
        sys.stdout = sys.__stdout__
        # Dispose of StringIO object.
        self.capturedOutput.close()

    def create_test_file(self, filename):
        # Helper function to create a file with the specified name in the test directory
        path = os.path.join(self.test_dir, filename)
        with open(path, "w") as f:
            f.write("test content")
        return path

    def test_suffix_counting__multiple_files(self):
        # Test suffix counting with multiple files having different suffixes
        filenames = ["file1_test.txt", "file2_test.doc", "file3_sample.txt"]
        for filename in filenames:
            self.create_test_file(filename)
        count_suffixes_in_folder(self.test_dir)
        output = self.capturedOutput.getvalue()
        self.assertIn("SUFFIX COUNT for _test: 2", output)
        self.assertIn("SUFFIX COUNT for _sample: 1", output)

    def test_suffix_counting__no_suffix(self):
        # Test with files that do not have any recognizable suffix
        filenames = ["file1", "file2", "file3"]
        for filename in filenames:
            self.create_test_file(filename)

        count_suffixes_in_folder(self.test_dir)
        output = self.capturedOutput.getvalue()
        self.assertEqual(output.strip(), '')  # No output should be generated

    def test_suffix_counting__invalid_directory(self):
        # Test error handling when the specified directory does not exist
        with self.assertRaises(ValueError):
            count_suffixes_in_folder("/path/to/nonexistent/directory")

class TestCheckIfDuplicateFilename(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove all files in the temporary directory
        for filename in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, filename)
            os.unlink(file_path)
        # Remove the temporary directory
        os.rmdir(self.test_dir)

    def create_test_file(self, filename):
        # Helper function to create a file with the specified name in the test directory
        path = os.path.join(self.test_dir, filename)
        with open(path, "w") as f:
            f.write("test content")
        return path

    def test_check_if_duplicate_filename__no_duplicate_exclude_suffix(self):
        # Test when there's no duplicate and exclude_suffix is True
        self.create_test_file("file1_test.txt")
        result = check_if_duplicate_filename("file2_test.txt", self.test_dir)
        self.assertFalse(result)

    def test_check_if_duplicate_filename__duplicate_exclude_suffix(self):
        # Test when there's a duplicate and exclude_suffix is True
        self.create_test_file("file1_test.txt")
        result = check_if_duplicate_filename("file1_other.txt", self.test_dir)
        self.assertTrue(result)

    def test_check_if_duplicate_filename__no_duplicate_include_suffix(self):
        # Test when there's no duplicate and exclude_suffix is False
        self.create_test_file("file1_test.txt")
        result = check_if_duplicate_filename("file1_other.txt", self.test_dir, exclude_suffix=False)
        self.assertFalse(result)

    def test_check_if_duplicate_filename__duplicate_include_suffix(self):
        # Test when there's a duplicate and exclude_suffix is False
        self.create_test_file("file1_test.txt")
        result = check_if_duplicate_filename("file1_test.txt", self.test_dir, exclude_suffix=False)
        self.assertTrue(result)

    def test_check_if_duplicate_filename__no_suffix(self):
        # Test with files that have no suffix
        self.create_test_file("file1.txt")
        result = check_if_duplicate_filename("file1.txt", self.test_dir)
        self.assertTrue(result)

    def test_check_if_duplicate_filename__empty_folder(self):
        # Test with an empty folder
        result = check_if_duplicate_filename("file1_test.txt", self.test_dir)
        self.assertFalse(result)

    def test_check_if_duplicate_filename__multiple_suffixes(self):
        # Test with multiple suffixes
        self.create_test_file("file1_test_v1.txt")
        result = check_if_duplicate_filename("file1_other_v2.txt", self.test_dir)
        self.assertFalse(result)

    def test_check_if_duplicate_filename__case_sensitivity(self):
        # Test case sensitivity
        self.create_test_file("File1_Test.txt")
        result = check_if_duplicate_filename("file1_test.txt", self.test_dir)
        self.assertTrue(result)  # Now case-insensitive

    def test_check_if_duplicate_filename__invalid_folder(self):
        # Test with an invalid folder path
        with self.assertRaises(FileNotFoundError):
            check_if_duplicate_filename("file1.txt", "/nonexistent/folder")


### TIME AND TIMESTAMP
class TestConvertSecondsToTimestamp(unittest.TestCase):
    def test_convert_seconds_to_timestamp__returns_correct_format_for_hours_minutes_seconds(self):
        # Testing for a time that includes hours, minutes, and seconds
        self.assertEqual(convert_seconds_to_timestamp(3665), "1:01:05")

    def test_convert_seconds_to_timestamp__returns_correct_format_for_minutes_seconds(self):
        # Testing for a time that includes minutes and seconds but no hours
        self.assertEqual(convert_seconds_to_timestamp(65), "1:05")

    def test_convert_seconds_to_timestamp__returns_correct_format_for_seconds_only(self):
        # Testing for a time that includes seconds only
        self.assertEqual(convert_seconds_to_timestamp(45), "0:45")

    def test_convert_seconds_to_timestamp__edge_case_of_zero_seconds(self):
        # Edge case: Exactly 0 seconds
        self.assertEqual(convert_seconds_to_timestamp(0), "0:00")

    def test_convert_seconds_to_timestamp__edge_case_of_exactly_one_hour(self):
        # Edge case: Exactly one hour
        self.assertEqual(convert_seconds_to_timestamp(3600), "1:00:00")

    def test_convert_seconds_to_timestamp__edge_case_of_exactly_one_minute(self):
        # Edge case: Exactly one minute
        self.assertEqual(convert_seconds_to_timestamp(60), "1:00")

    def test_convert_seconds_to_timestamp__value_error_raised_for_negative_input(self):
        # Testing for ValueError on negative input (invalid input scenario)
        with self.assertRaises(ValueError):
            convert_seconds_to_timestamp(-1)

    def test_convert_seconds_to_timestamp__value_error_raised_for_non_integer_input(self):
        # Testing for ValueError on non-integer input
        with self.assertRaises(TypeError):
            convert_seconds_to_timestamp("a string")

class TestConvertTimestampToSeconds(unittest.TestCase):
    def test_convert_timestamp_to_seconds__correct_conversion_hh_mm_ss(self):
        # Testing correct conversion from hh:mm:ss to total seconds
        self.assertEqual(convert_timestamp_to_seconds("01:02:03"), 3723)

    def test_convert_timestamp_to_seconds__correct_conversion_mm_ss(self):
        # Testing correct conversion from mm:ss to total seconds
        self.assertEqual(convert_timestamp_to_seconds("02:03"), 123)

    def test_convert_timestamp_to_seconds__non_string_input_raises_type_error(self):
        # Testing that non-string input raises TypeError
        with self.assertRaises(TypeError):
            convert_timestamp_to_seconds(123)

    def test_convert_timestamp_to_seconds__invalid_format_raises_value_error(self):
        # Testing that an invalid format raises ValueError
        with self.assertRaises(ValueError):
            convert_timestamp_to_seconds("01:02:03:04")

    def test_convert_timestamp_to_seconds__non_numeric_characters_raise_value_error(self):
        # Testing that non-numeric characters in the input raise ValueError
        with self.assertRaises(ValueError):
            convert_timestamp_to_seconds("01:xx:03")

    def test_convert_timestamp_to_seconds__out_of_range_hours_raises_value_error(self):
        # Testing that hours out of valid range raise ValueError
        with self.assertRaises(ValueError):
            convert_timestamp_to_seconds("100:00:00")

    def test_convert_timestamp_to_seconds__out_of_range_minutes_raises_value_error(self):
        # Testing that minutes out of valid range raise ValueError
        with self.assertRaises(ValueError):
            convert_timestamp_to_seconds("00:60:00")

    def test_convert_timestamp_to_seconds__out_of_range_seconds_raises_value_error(self):
        # Testing that seconds out of valid range raise ValueError
        with self.assertRaises(ValueError):
            convert_timestamp_to_seconds("00:00:60")

class TestChangeTimestamp(unittest.TestCase):
    def test_change_timestamp__increases_timestamp_correctly(self):
        # Test increasing a timestamp successfully
        self.assertEqual(change_timestamp("01:01:01", 3661), "2:02:02")

    def test_change_timestamp__decreases_timestamp_correctly(self):
        # Test decreasing a timestamp successfully
        self.assertEqual(change_timestamp("02:02:02", -3661), "1:01:01")

    def test_change_timestamp__handles_zero_delta_seconds(self):
        # Test that timestamp remains unchanged with delta_seconds = 0
        self.assertEqual(change_timestamp("01:00:00", 0), "1:00:00")

    def test_change_timestamp__none_input_raises_value_error(self):
        # Test that None timestamp input raises ValueError
        with self.assertRaises(ValueError):
            change_timestamp(None, 60)

    def test_change_timestamp__negative_raises_value_error(self):
        # Test that negative modified seconds raises ValueError
        with self.assertRaises(ValueError):
            change_timestamp("00:00:01", -2)

    def test_change_timestamp__large_positive_delta_rolls_over_days(self):
        # Test a large delta that rolls over multiple days
        # Assuming the output format is always "hh:mm:ss" even for values exceeding 24 hours
        self.assertEqual(change_timestamp("00:00:00", 86400 + 3661), "25:01:01")

class TestTuneTimestamp(unittest.TestCase):
    def test_tune_timestamp__correct_format_conversion(self):
        # Test that the timestamp is correctly "tuned" or normalized
        self.assertEqual(tune_timestamp("01:02:03"), "1:02:03")

    def test_tune_timestamp__handles_leading_zeros(self):
        # Test that leading zeros are handled correctly
        self.assertEqual(tune_timestamp("01:00:00"), "1:00:00")

    def test_tune_timestamp__handles_none_input(self):
        # Test that None input is handled by returning None
        self.assertIsNone(tune_timestamp(None))

    def test_tune_timestamp__input_output_equality_for_valid_timestamps(self):
        # Test that valid timestamps are returned in standard format
        self.assertEqual(tune_timestamp("12:34:56"), "12:34:56")

    def test_tune_timestamp__adjusts_minute_and_second_format(self):
        # Test that minutes and seconds are always returned with two digits
        self.assertEqual(tune_timestamp("0:2:9"), "2:09")

    def test_tune_timestamp__with_positive_delta(self):
        # Test adding positive seconds to timestamp
        self.assertEqual(tune_timestamp("1:00:00", delta_seconds=65), "1:01:05")
        self.assertEqual(tune_timestamp("59:59", delta_seconds=1), "1:00:00")

    def test_tune_timestamp__with_negative_delta(self):
        # Test subtracting seconds from timestamp
        self.assertEqual(tune_timestamp("1:01:05", delta_seconds=-65), "1:00:00")
        self.assertEqual(tune_timestamp("1:00:00", delta_seconds=-1), "59:59")

    def test_tune_timestamp__with_invalid_delta_type(self):
        # Test that non-integer delta_seconds raises ValueError
        with self.assertRaises(ValueError):
            tune_timestamp("1:00:00", delta_seconds="5")
        with self.assertRaises(ValueError):
            tune_timestamp("1:00:00", delta_seconds=1.5)

    def test_tune_timestamp__with_negative_result(self):
        # Test that attempting to subtract more seconds than available raises ValueError
        with self.assertRaises(ValueError):
            tune_timestamp("0:00:30", delta_seconds=-31)

    def test_tune_timestamp__with_zero_delta(self):
        # Test that zero delta_seconds doesn't change the timestamp
        self.assertEqual(tune_timestamp("1:23:45", delta_seconds=0), "1:23:45")

class TestGetTimestamp(unittest.TestCase):

    def test_get_timestamp__with_valid_timestamp(self):
        line = "David Deutsch  [3:18](https://www.youtube.com/dummylink&t=198)  SKIPQA"
        expected_timestamp = "3:18"
        expected_index = 15
        if print_get_timestamp_flag:
            print_chars_with_indices(line,25)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

    def test_get_timestamp__with_invalid_timestamp(self):
        line = "Bob McBobbin  99:99:99 should not be accepted."
        with self.assertRaises(ValueError):
            get_timestamp(line)

    def test_get_timestamp__with_timestamp_without_hours(self):
        line = "Quick example [12:34] with no hours."
        expected_timestamp = "12:34"
        expected_index = 14
        if print_get_timestamp_flag:
            print_chars_with_indices(line,25)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

    def test_get_timestamp__with_line_with_excessive_words_around_timestamp(self):
        line = "This is a line with a lot of words before the timestamp [1:23:45] and also a lot of words after the timestamp."
        expected_timestamp = None
        expected_index = None
        if print_get_timestamp_flag:
            print_chars_with_indices(line,60)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

    def test_get_timestamp__with_line_with_no_timestamp(self):
        line = "This line does not contain a timestamp at all."
        expected_timestamp = None
        expected_index = None
        if print_get_timestamp_flag:
            print_chars_with_indices(line,25)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

    def test_get_timestamp__with_line_with_timestamp_and_no_link(self):
        line = "Here is a timestamp 2:34 without a link."
        expected_timestamp = "2:34"
        expected_index = 20
        if print_get_timestamp_flag:
            print_chars_with_indices(line,25)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

    def test_get_timestamp__with_line_with_timestamp_and_link(self):
        line = "Timestamp with link [5:27](https://www.example.com) should be found."
        expected_timestamp = "5:27"
        expected_index = 20
        if print_get_timestamp_flag:
            print_chars_with_indices(line,25)
        timestamp, index = get_timestamp(line, print_line=print_get_timestamp_flag)
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(index, expected_index)

class TestGetCurrentDatetimeHumanfriendly(unittest.TestCase):
    def test_get_current_datetime_humanfriendly__default_timezone(self):
        result = get_current_datetime_humanfriendly()
        expected_timezones = ["UTC-08:00 America/Los_Angeles", "UTC-07:00 America/Los_Angeles"]
        # Check if any of the expected timezone strings is in the result
        self.assertTrue(any(tz in result for tz in expected_timezones))

    def test_get_current_datetime_humanfriendly__specific_timezone(self):
        result = get_current_datetime_humanfriendly(timezone='UTC')
        expected_timezone = 'UTC'
        self.assertIn(expected_timezone, result)
        # Check for UTC offset in the result
        self.assertTrue("UTC+00:00" in result)

    def test_get_current_datetime_humanfriendly__format(self):
        result = get_current_datetime_humanfriendly(include_timezone=False)
        try:
            datetime.strptime(result, '%Y-%m-%d %H:%M:%S')
            format_valid = True
        except ValueError:
            format_valid = False
        self.assertTrue(format_valid)

    def test_get_current_datetime_humanfriendly__include_timezone_false(self):
        result = get_current_datetime_humanfriendly(include_timezone=False)
        self.assertNotIn('UTC', result)
        self.assertNotIn('America', result)
        try:
            datetime.strptime(result, '%Y-%m-%d %H:%M:%S')
            format_valid = True
        except ValueError:
            format_valid = False
        self.assertTrue(format_valid)

class TestConvertToEpochSeconds(unittest.TestCase):
    def test_convert_to_epoch_seconds_various_formats(self):
        datetime_list = [
            "2024-05-04 11:42:26",
            "2024-05-04 11:42:26 UTC-07:00 America/Los_Angeles",
            "2024-05-04 11:42:26 America/Los_Angeles",
            "2024-05-04 11:42:26 America/Denver",
            "2024-05-04_114226",
            "2024-05-04_114226_UTC-0600"
        ]
        expected_results = [
            1714848146.0,
            1714848146.0,
            1714848146.0,
            1714844546.0,
            1714848146.0,
            1714844546.0
        ]
        for datetime_string, expected in zip(datetime_list, expected_results):
            with self.subTest(datetime_string=datetime_string):
                result = convert_to_epoch_seconds(datetime_string, verbose=True)
                self.assertEqual(result, expected)

class TestGetElapsedSeconds(unittest.TestCase):
    def test_get_elapsed_seconds__valid(self):
        start_time = time.time() - 90  # 1.5 minutes ago
        elapsed_time = get_elapsed_seconds(start_time)
        self.assertEqual(elapsed_time, 90)

    def test_get_elapsed_time__invalid_input(self):
        start_time = "invalid input"
        with self.assertRaises(TypeError):
            get_elapsed_seconds(start_time)

class TestTrackProgress(unittest.TestCase):
    def setUp(self):
        self.start_time = time.time()

    def test_track_progress__basic_progress(self):
        # Test basic progress reporting at first checkpoint (2%)
        with patch('builtins.print') as mock_print:
            last_percentage = track_progress(10, 100, self.start_time, 0)
            self.assertEqual(last_percentage, 2)  # First checkpoint is 2%
            mock_print.assert_called_once()
            self.assertIn("10% complete", mock_print.call_args[0][0])

    def test_track_progress__small_item_count(self):
        # Test with small total count where early checkpoints should be skipped
        with patch('builtins.print') as mock_print:
            # With 3 items, each item represents ~33.3%
            last_percentage = track_progress(1, 3, self.start_time, 0)
            self.assertEqual(last_percentage, 0)  # No progress reported yet
            mock_print.assert_not_called()

            # At 2 items (66.7%), should hit the 40% checkpoint
            last_percentage = track_progress(2, 3, self.start_time, last_percentage)
            self.assertEqual(last_percentage, 40)  # First checkpoint that represents >= 1 item
            self.assertEqual(mock_print.call_count, 1)
            self.assertIn("66% complete", mock_print.call_args[0][0])

    def test_track_progress__custom_item_name(self):
        # Test with custom item name
        with patch('builtins.print') as mock_print:
            last_percentage = track_progress(10, 100, self.start_time, 0, item_name="files")
            self.assertEqual(last_percentage, 2)  # First checkpoint is 2%
            mock_print.assert_called_once()
            self.assertIn("files", mock_print.call_args[0][0])

    def test_track_progress__multiple_checkpoints(self):
        # Test hitting multiple checkpoints
        with patch('builtins.print') as mock_print:
            last_percentage = 0
            # Should hit 2% checkpoint
            last_percentage = track_progress(2, 100, self.start_time, last_percentage)
            self.assertEqual(last_percentage, 2)
            
            # Should hit 5% checkpoint
            last_percentage = track_progress(5, 100, self.start_time, last_percentage)
            self.assertEqual(last_percentage, 5)
            
            # Should hit 10% checkpoint
            last_percentage = track_progress(10, 100, self.start_time, last_percentage)
            self.assertEqual(last_percentage, 10)
            
            self.assertEqual(mock_print.call_count, 3)

    def test_track_progress__no_progress(self):
        # Test when progress hasn't reached next checkpoint
        with patch('builtins.print') as mock_print:
            last_percentage = track_progress(1, 100, self.start_time, 0)
            self.assertEqual(last_percentage, 0)  # No checkpoint reached
            mock_print.assert_not_called()

    def test_track_progress__completion(self):
        # Test reaching 100% completion
        with patch('builtins.print') as mock_print:
            last_percentage = track_progress(100, 100, self.start_time, 90)
            self.assertEqual(last_percentage, 100)
            mock_print.assert_called_once()
            self.assertIn("100% complete", mock_print.call_args[0][0])

    def test_track_progress__zero_total(self):
        # Test handling of zero total items
        with patch('builtins.print') as mock_print:
            with self.assertRaises(ValueError):
                track_progress(0, 0, self.start_time, 0)
            mock_print.assert_not_called()

### TIMESTAMP LINKS
class TestRemoveTimestampLinksFromContent(unittest.TestCase):
    def test_remove_timestamp_links_from_content__with_links(self):
        original_content = "John  [1:00](Link 1)\nBill  [2:00](Link 2)\nNormal text\n"
        expected_content = "John  1:00\nBill  2:00\nNormal text\n"
        processed_content = remove_timestamp_links_from_content(original_content)
        self.assertEqual(processed_content, expected_content)

    def test_remove_timestamp_links_from_content__with_links_text_after(self):
        original_content = "John  [1:00](Link 1)  AFTER\nBill  [2:00](Link 2)\nNormal text\n"
        expected_content = "John  1:00  AFTER\nBill  2:00\nNormal text\n"
        processed_content = remove_timestamp_links_from_content(original_content)
        self.assertEqual(processed_content, expected_content)

    def test_remove_timestamp_links_from_content__no_links(self):
        original_content = "No links here\nJust normal text\n"
        expected_content = "No links here\nJust normal text\n"
        processed_content = remove_timestamp_links_from_content(original_content)
        self.assertEqual(processed_content, expected_content)

    def test_remove_timestamp_links_from_content__empty_content(self):
        original_content = ""
        expected_content = "\n"  # Function adds an extra newline
        processed_content = remove_timestamp_links_from_content(original_content)
        self.assertEqual(processed_content, expected_content)

class TestRemoveTimestampLinks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filename = os.path.join(self.temp_dir.name, 'test_file.md')
        self.metadata = "## metadata\nTitle: Test File\nAuthor: John Doe\n"
        self.content = "## content\nJohn  [1:00](Link 1)\nBill  [2:00](Link 2)\nNormal text\n"
        self.file_content = self.metadata + "\n\n" + self.content

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_temp_file_with_content(self, content):
        with open(self.test_filename, 'w') as f:
            f.write(content)

    @patch('core.fileops.read_file_flex')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.write_metadata_and_content')
    def test_remove_timestamp_links__with_metadata(self, mock_write, mock_remove, mock_read):
        mock_read.return_value = (self.metadata, self.content)
        mock_remove.return_value = "John  1:00\nBill  2:00\nNormal text\n"
        
        remove_timestamp_links(self.test_filename)
        
        mock_read.assert_called_once_with(self.test_filename)
        mock_remove.assert_called_once_with(self.content)
        mock_write.assert_called_once_with(self.test_filename, self.metadata, 
                                           "John  1:00\nBill  2:00\nNormal text\n", 
                                           suffix_new='_temp', overwrite='yes')

    @patch('core.fileops.read_file_flex')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.write_complete_text')
    def test_remove_timestamp_links__without_metadata(self, mock_write, mock_remove, mock_read):
        mock_read.return_value = (None, self.content)
        mock_remove.return_value = "John  1:00\nBill  2:00\nNormal text\n"
        
        remove_timestamp_links(self.test_filename)
        
        mock_read.assert_called_once_with(self.test_filename)
        mock_remove.assert_called_once_with(self.content)
        mock_write.assert_called_once_with(self.test_filename, 
                                           "John  1:00\nBill  2:00\nNormal text\n", 
                                           overwrite='yes')

    @patch('core.fileops.read_file_flex')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.write_metadata_and_content')
    def test_remove_timestamp_links__empty_content(self, mock_write, mock_remove, mock_read):
        mock_read.return_value = (self.metadata, "")
        mock_remove.return_value = ""
        
        remove_timestamp_links(self.test_filename)
        
        mock_remove.assert_called_once_with("")
        mock_write.assert_called_once_with(self.test_filename, self.metadata, "", 
                                           suffix_new='_temp', overwrite='yes')

    @patch('core.fileops.read_file_flex')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.write_metadata_and_content')
    def test_remove_timestamp_links__no_timestamp_links(self, mock_write, mock_remove, mock_read):
        content_without_links = "## content\nJohn 1:00\nBill 2:00\nNormal text\n"
        mock_read.return_value = (self.metadata, content_without_links)
        mock_remove.return_value = content_without_links
        
        remove_timestamp_links(self.test_filename)
        
        mock_remove.assert_called_once_with(content_without_links)
        mock_write.assert_called_once_with(self.test_filename, self.metadata, content_without_links, 
                                           suffix_new='_temp', overwrite='yes')

    @patch('core.fileops.read_file_flex', side_effect=FileNotFoundError)
    def test_remove_timestamp_links__file_not_found(self, mock_read):
        with self.assertRaises(FileNotFoundError):
            remove_timestamp_links(self.test_filename)

    @patch('core.fileops.read_file_flex')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.write_metadata_and_content', side_effect=IOError)
    def test_remove_timestamp_links__write_error(self, mock_write, mock_remove, mock_read):
        mock_read.return_value = (self.metadata, self.content)
        mock_remove.return_value = "John  1:00\nBill  2:00\nNormal text\n"
        
        with self.assertRaises(IOError):
            remove_timestamp_links(self.test_filename)

    def test_remove_timestamp_links__integration(self):
        self.create_temp_file_with_content(self.file_content)

        remove_timestamp_links(self.test_filename)

        with open(self.test_filename, 'r') as f:
            new_content = f.read()

        expected_content = self.metadata + "\n\n" + "## content\nJohn  1:00\nBill  2:00\nNormal text\n"
        self.assertEqual(new_content, expected_content)

    def test_remove_timestamp_links__integration_without_metadata(self):
        content_without_metadata = "## content\nJohn  [1:00](Link 1)\nBill  [2:00](Link 2)\nNormal text\n"
        self.create_temp_file_with_content(content_without_metadata)

        remove_timestamp_links(self.test_filename)

        with open(self.test_filename, 'r') as f:
            new_content = f.read()

        expected_content = "## content\nJohn  1:00\nBill  2:00\nNormal text\n"
        self.assertEqual(new_content, expected_content)

class TestGenerateTimestampLink(unittest.TestCase):
    def test_generate_timestamp_link__youtube(self):
        base_link = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        timestamp = "1:00"
        expected_link = "[1:00](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=60)"
        self.assertEqual(generate_timestamp_link(base_link, timestamp), expected_link)

    def test_generate_timestamp_link__vimeo(self):
        base_link = "https://vimeo.com/123456789"
        timestamp = "1:00"
        expected_link = "[1:00](https://vimeo.com/123456789?ts=60000)"
        self.assertEqual(generate_timestamp_link(base_link, timestamp), expected_link)

    def test_generate_timestamp_link__spotify(self):
        base_link = "https://open.spotify.com/track/abcde12345"
        timestamp = "1:00"
        expected_link = "[1:00](https://open.spotify.com/track/abcde12345?t=60)"
        self.assertEqual(generate_timestamp_link(base_link, timestamp), expected_link)

    def test_generate_timestamp_link__unknown_domain(self):
        base_link = "https://unknown.com/video/abc"
        timestamp = "1:00"
        expected_link = "[1:00](https://unknown.com/video/abc&t=60)"
        self.assertEqual(generate_timestamp_link(base_link, timestamp), expected_link)

class TestAddTimestampLinksToContent(unittest.TestCase):
    def test_add_timestamp_links_to_content__with_timestamps_youtube_watch(self):
        base_link = "https://www.youtube.com/watch?v=2BLo2SdmjLI"
        original_content = "John  1:00\nBill  2:00\nNormal text\n"
        expected_content = "John  [1:00](https://www.youtube.com/watch?v=2BLo2SdmjLI&t=60)\nBill  [2:00](https://www.youtube.com/watch?v=2BLo2SdmjLI&t=120)\nNormal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)

    def test_add_timestamp_links_to_content__with_timestamps_youtube_dotbe(self):
        base_link = "https://youtu.be/vYNLahd6fds"
        original_content = "John  1:00\nBill  2:00\nNormal text\n"
        expected_content = "John  [1:00](https://youtu.be/vYNLahd6fds&t=60)\nBill  [2:00](https://youtu.be/vYNLahd6fds&t=120)\nNormal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)

    def test_add_timestamp_links_to_content__with_timestamps_spotify(self):
        base_link = "https://open.spotify.com/episode/2YJea3yl6k0ORFbJAwuELg?si=KfB2VaOiRyy64XFmxn3YHQ"
        original_content = "John  1:00\nBill  2:00\nNormal text\n"
        expected_content = "John  [1:00](https://open.spotify.com/episode/2YJea3yl6k0ORFbJAwuELg?si=KfB2VaOiRyy64XFmxn3YHQ?t=60)\nBill  [2:00](https://open.spotify.com/episode/2YJea3yl6k0ORFbJAwuELg?si=KfB2VaOiRyy64XFmxn3YHQ?t=120)\nNormal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)

    def test_add_timestamp_links_to_content__with_timestamps_vimeo(self):
        base_link = "https://vimeo.com/668273372/14ec57a5d7"
        original_content = "John  1:00\nBill  2:00\nNormal text\n"
        expected_content = "John  [1:00](https://vimeo.com/668273372/14ec57a5d7?ts=60000)\nBill  [2:00](https://vimeo.com/668273372/14ec57a5d7?ts=120000)\nNormal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)
 
    def test_add_timestamp_links_to_content__with_timestamps_text_after(self):
        base_link = "https://www.youtube.com/watch?v=2BLo2SdmjLI"
        original_content = "John  1:00 AFTER\nBill  2:00\nNormal text\n"
        expected_content = "John  [1:00](https://www.youtube.com/watch?v=2BLo2SdmjLI&t=60) AFTER\nBill  [2:00](https://www.youtube.com/watch?v=2BLo2SdmjLI&t=120)\nNormal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)

    def test_add_timestamp_links_to_content__no_timestamps(self):
        base_link = "https://youtube.com/video"
        original_content = "No timestamps here\nJust normal text\n"
        expected_content = "No timestamps here\nJust normal text\n"
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)

    def test_add_timestamp_links_to_content__empty_content(self):
        base_link = "https://example.com/video"
        original_content = ""
        expected_content = "\n"  # Function adds an extra newline
        processed_content = add_timestamp_links_to_content(original_content, base_link)
        self.assertEqual(processed_content, expected_content)
class TestGetLinkFromMetadata(unittest.TestCase):
    def setUp(self):
        self.test_filename = 'test_link_metadata.md'

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_get_link_from_metadata__simple_link_field(self):
        # Test with simple "link:" field
        metadata = "## metadata\nlink: https://example.com/video\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://example.com/video")

    def test_get_link_from_metadata__youtube_link_field(self):
        # Test with "link youtube:" field
        metadata = "## metadata\nlink youtube: https://youtube.com/watch?v=123\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://youtube.com/watch?v=123")

    def test_get_link_from_metadata__spotify_link_field(self):
        # Test with "link spotify:" field
        metadata = "## metadata\nlink spotify: https://open.spotify.com/episode/123\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://open.spotify.com/episode/123")

    def test_get_link_from_metadata__multiple_link_fields(self):
        # Test with multiple link fields - should return the first one found
        metadata = "## metadata\nlink youtube: https://youtube.com/watch?v=123\nlink spotify: https://open.spotify.com/episode/456\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://youtube.com/watch?v=123")

    def test_get_link_from_metadata__no_link_field(self):
        # Test with no link field
        metadata = "## metadata\ntitle: Test Title\nauthor: Test Author\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertIsNone(result)

    def test_get_link_from_metadata__fallback_to_extended_format(self):
        # Test fallback: no simple "link:" but has "link youtube:"
        metadata = "## metadata\ntitle: Test Title\nlink youtube: https://youtube.com/watch?v=789\n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://youtube.com/watch?v=789")

    def test_get_link_from_metadata__link_with_extra_spaces(self):
        # Test with extra spaces around the link value
        metadata = "## metadata\nlink youtube:   https://youtube.com/watch?v=123   \n"
        content = "## content\nSome content here.\n"
        
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata}\n{content}")

        result = get_link_from_metadata(self.test_filename)
        self.assertEqual(result, "https://youtube.com/watch?v=123")

    @patch('core.fileops.read_metadata_field_from_file')
    @patch('core.fileops.read_metadata_and_content')
    def test_get_link_from_metadata__mock_simple_link(self, mock_read_metadata, mock_read_field):
        # Test mocked simple link field
        mock_read_field.return_value = (2, "https://example.com/video")
        
        result = get_link_from_metadata(self.test_filename)
        
        self.assertEqual(result, "https://example.com/video")
        mock_read_field.assert_called_once_with(self.test_filename, "link")
        mock_read_metadata.assert_not_called()

    @patch('core.fileops.read_metadata_field_from_file')
    @patch('core.fileops.read_metadata_and_content')
    def test_get_link_from_metadata__mock_fallback_to_extended(self, mock_read_metadata, mock_read_field):
        # Test mocked fallback to extended format
        mock_read_field.return_value = (None, None)
        mock_read_metadata.return_value = ("## metadata\nlink youtube: https://youtube.com/watch?v=456\n", "## content\nTest content\n")
        
        result = get_link_from_metadata(self.test_filename)
        
        self.assertEqual(result, "https://youtube.com/watch?v=456")
        mock_read_field.assert_called_once_with(self.test_filename, "link")
        mock_read_metadata.assert_called_once_with(self.test_filename)

    @patch('core.fileops.read_metadata_field_from_file')
    @patch('core.fileops.read_metadata_and_content')
    def test_get_link_from_metadata__mock_no_link_found(self, mock_read_metadata, mock_read_field):
        # Test mocked no link found
        mock_read_field.return_value = (None, None)
        mock_read_metadata.return_value = ("## metadata\ntitle: Test Title\n", "## content\nTest content\n")
        
        result = get_link_from_metadata(self.test_filename)
        
        self.assertIsNone(result)
        mock_read_field.assert_called_once_with(self.test_filename, "link")
        mock_read_metadata.assert_called_once_with(self.test_filename)

class TestAddTimestampLinks(unittest.TestCase):
    def setUp(self):
        self.test_filename = 'test_file.md'
        self.metadata = "## metadata\nlink: https://example.com/video\n"
        self.content = "## content\n\nJohn  1:00\nHi There.\nBill  2:00\nI like turtles.\n"
        self.file_content = f"{self.metadata}\n{self.content}"
        
        with open(self.test_filename, 'w') as f:
            f.write(self.file_content)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    @patch('core.fileops.read_metadata_and_content')
    @patch('core.fileops.get_link_from_metadata')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.add_timestamp_links_to_content')
    @patch('core.fileops.write_metadata_and_content')
    def test_add_timestamp_links__basic_functionality(self, mock_write, mock_add, mock_remove, mock_get_link, mock_read):
        mock_read.return_value = (self.metadata, self.content)
        mock_get_link.return_value = "https://example.com/video"
        mock_remove.return_value = self.content
        mock_add.return_value = "John  [1:00](https://example.com/video&t=60)\nHi There.\nBill  [2:00](https://example.com/video&t=120)\nI like turtles.\n"

        add_timestamp_links(self.test_filename)

        mock_read.assert_called_once_with(self.test_filename)
        mock_get_link.assert_called_once_with(self.test_filename)
        mock_remove.assert_called_once_with(self.content)
        mock_add.assert_called_once_with(self.content, "https://example.com/video")
        mock_write.assert_called_once_with(self.test_filename, self.metadata, mock_add.return_value, suffix_new='_temp', overwrite='yes')

    @patch('core.fileops.read_metadata_and_content')
    @patch('core.fileops.get_link_from_metadata')
    @patch('builtins.print')
    def test_add_timestamp_links__missing_link_metadata(self, mock_print, mock_get_link, mock_read):
        mock_read.return_value = (self.metadata, self.content)
        mock_get_link.return_value = None

        add_timestamp_links(self.test_filename)

        mock_read.assert_called_once_with(self.test_filename)
        mock_get_link.assert_called_once_with(self.test_filename)
        mock_print.assert_called_once_with(f"Warning: No link field found in metadata for {self.test_filename}")

    @patch('core.fileops.read_metadata_and_content')
    @patch('core.fileops.get_link_from_metadata')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.add_timestamp_links_to_content')
    @patch('core.fileops.write_metadata_and_content')
    def test_add_timestamp_links__empty_content(self, mock_write, mock_add, mock_remove, mock_get_link, mock_read):
        mock_read.return_value = (self.metadata, "")
        mock_get_link.return_value = "https://example.com/video"
        mock_remove.return_value = ""
        mock_add.return_value = ""

        add_timestamp_links(self.test_filename)

        mock_add.assert_called_once_with("", "https://example.com/video")
        mock_write.assert_called_once_with(self.test_filename, self.metadata, "", suffix_new='_temp', overwrite='yes')

    @patch('core.fileops.read_metadata_and_content', side_effect=FileNotFoundError)
    def test_add_timestamp_links__file_not_found(self, mock_read):
        with self.assertRaises(FileNotFoundError):
            add_timestamp_links(self.test_filename)

    @patch('core.fileops.read_metadata_and_content')
    @patch('core.fileops.get_link_from_metadata')
    @patch('core.fileops.remove_timestamp_links_from_content')
    @patch('core.fileops.add_timestamp_links_to_content')
    @patch('core.fileops.write_metadata_and_content', side_effect=IOError)
    def test_add_timestamp_links__write_error(self, mock_write, mock_add, mock_remove, mock_get_link, mock_read):
        mock_read.return_value = (self.metadata, self.content)
        mock_get_link.return_value = "https://example.com/video"
        mock_remove.return_value = self.content
        mock_add.return_value = "John  [1:00](https://example.com/video&t=60)\nHi There.\nBill  [2:00](https://example.com/video&t=120)\nI like turtles.\n"

        with self.assertRaises(IOError):
            add_timestamp_links(self.test_filename)

    def test_add_timestamp_links__integration(self):
        add_timestamp_links(self.test_filename)

        with open(self.test_filename, 'r') as f:
            new_content = f.read()

        expected_content = (
            "## metadata\nlink: https://example.com/video\n\n\n"
            "## content\n\n"
            "John  [1:00](https://example.com/video&t=60)\nHi There.\n"
            "Bill  [2:00](https://example.com/video&t=120)\nI like turtles.\n"
        )
        self.assertEqual(new_content, expected_content)

    def test_add_timestamp_links__integration_with_existing_links(self):
        content_with_links = (
            "## content\n\n"
            "John  [1:00](https://example.com/video&t=60)\nHi There.\n"
            "Bill  [2:00](https://example.com/video&t=120)\nI like turtles.\n"
        )
        with open(self.test_filename, 'w') as f:
            f.write(f"{self.metadata}\n{content_with_links}")

        add_timestamp_links(self.test_filename)

        with open(self.test_filename, 'r') as f:
            new_content = f.read()

        expected_content = f"{self.metadata}\n\n{content_with_links}"
        self.assertEqual(new_content, expected_content)

    def test_add_timestamp_links__integration_with_new_link_format(self):
        # Test with new link format (e.g., "link youtube:")
        metadata_new_format = "## metadata\nlink youtube: https://youtube.com/watch?v=123\n"
        with open(self.test_filename, 'w') as f:
            f.write(f"{metadata_new_format}\n{self.content}")

        add_timestamp_links(self.test_filename)

        with open(self.test_filename, 'r') as f:
            new_content = f.read()

        expected_content = (
            "## metadata\nlink youtube: https://youtube.com/watch?v=123\n\n\n"
            "## content\n\n"
            "John  [1:00](https://youtube.com/watch?v=123&t=60)\nHi There.\n"
            "Bill  [2:00](https://youtube.com/watch?v=123&t=120)\nI like turtles.\n"
        )
        self.assertEqual(new_content, expected_content)

class TestGetTextBetweenDelimiters(unittest.TestCase):
    def setUp(self):
        # Suppress warnings in the test output
        warnings.simplefilter("ignore")

    def test_get_text_between_delimiters__start_and_end(self):
        # Test extraction of text between start and end delimiters
        full_text = "Start here: This is the text. End here."
        delimiter_start = "Start here:"
        delimiter_end = "End here."
        expected_text = "Start here: This is the text.\n"
        self.assertEqual(get_text_between_delimiters(full_text, delimiter_start, delimiter_end), expected_text)

    def test_get_text_between_delimiters__start_only(self):
        # Test extraction of text from start delimiter to end of text
        full_text = "Start here: This is the text."
        delimiter_start = "Start here:"
        expected_text = "Start here: This is the text.\n"
        self.assertEqual(get_text_between_delimiters(full_text, delimiter_start), expected_text)

    def test_get_text_between_delimiters__missing_start_delimiter(self):
        # Test when start delimiter is not found in the text
        full_text = "This is the text."
        delimiter_start = "Start here:"
        self.assertIsNone(get_text_between_delimiters(full_text, delimiter_start))

    def test_get_text_between_delimiters__missing_end_delimiter(self):
        # Test when end delimiter is not found in the text
        full_text = "Start here: This is the text."
        delimiter_start = "Start here:"
        delimiter_end = "End here."
        expected_text = "Start here: This is the text.\n"
        self.assertEqual(get_text_between_delimiters(full_text, delimiter_start, delimiter_end), expected_text)

    def test_get_text_between_delimiters__empty_text(self):
        # Test when the full_text is empty
        full_text = ""
        delimiter_start = "Start here:"
        self.assertIsNone(get_text_between_delimiters(full_text, delimiter_start))


### FIND AND REPLACE
class TestCountNumInstances(unittest.TestCase):
    def create_temp_file_with_content(self, content):
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.txt')
        temp_file.write(content)
        temp_file.seek(0)
        return temp_file

    def test_count_num_instances__multiple_occurrences(self):
        temp_file = self.create_temp_file_with_content("Hello world, hello Python. Hello unittest.")
        # Adjusting the expected count to match the actual occurrences of "Hello" in a case-sensitive manner
        self.assertEqual(count_num_instances(temp_file.name, "Hello"), 2)
        os.unlink(temp_file.name)

    def test_count_num_instances__no_occurrences(self):
        temp_file = self.create_temp_file_with_content("This is a test file without the keyword.")
        self.assertEqual(count_num_instances(temp_file.name, "nonexistent"), 0)
        os.unlink(temp_file.name)

    def test_count_num_instances__case_sensitive_search(self):
        temp_file = self.create_temp_file_with_content("hello Hello hEllo")
        self.assertEqual(count_num_instances(temp_file.name, "Hello"), 1)
        os.unlink(temp_file.name)

    def test_count_num_instances__empty_file(self):
        temp_file = self.create_temp_file_with_content("")
        self.assertEqual(count_num_instances(temp_file.name, "Hello"), 0)
        os.unlink(temp_file.name)

class TestFindAndReplacePairs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "test_file.txt")

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_temp_file_with_content(self, content):
        with open(self.file_path, 'w') as f:
            f.write(content)

    def test_find_and_replace_pairs__basic_replacement(self):
        self.create_temp_file_with_content("Hello world, hello Python.")
        find_replace_pairs = [("world", "universe"), ("Python", "Programming")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello universe, hello Programming.")

    def test_find_and_replace_pairs__no_replacements(self):
        self.create_temp_file_with_content("Hello world, hello Python.")
        find_replace_pairs = [("foo", "bar"), ("baz", "qux")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 0)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello world, hello Python.")

    def test_find_and_replace_pairs__no_metadata(self):
        self.create_temp_file_with_content("### myheading\n\nHello world.\nHello Python.")
        find_replace_pairs = [("world", "universe"), ("Python", "Programming")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "### myheading\n\nHello universe.\nHello Programming.")

    def test_find_and_replace_pairs__use_regex(self):
        self.create_temp_file_with_content("Hello world123, hello Python456.")
        find_replace_pairs = [(r"world\d+", "universe"), (r"Python\d+", "Programming")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs, use_regex=True)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello universe, hello Programming.")

    def test_find_and_replace_pairs__multiple_occurrences(self):
        self.create_temp_file_with_content("Hello hello hello, world world world.")
        find_replace_pairs = [("hello", "hi"), ("world", "universe")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 5)
        with open(self.file_path, 'r') as f:
            content = f.read()
        # Update the expected content to match the current behavior of the function
        self.assertEqual(content, "Hello hi hi, universe universe universe.")

    def test_find_and_replace_pairs__case_sensitive(self):
        self.create_temp_file_with_content("Hello HELLO hello, World WORLD world.")
        find_replace_pairs = [("hello", "hi"), ("world", "universe")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello HELLO hi, World WORLD universe.")

    def test_find_and_replace_pairs__empty_file(self):
        self.create_temp_file_with_content("")
        find_replace_pairs = [("hello", "hi"), ("world", "universe")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 0)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "")

    def test_find_and_replace_pairs__overlapping_replacements(self):
        self.create_temp_file_with_content("abcdefg")
        find_replace_pairs = [("abc", "ABC"), ("cde", "CDE")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 1)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "ABCdefg")

    def test_find_and_replace_pairs__regex_with_groups(self):
        self.create_temp_file_with_content("Hello world123, hello Python456.")
        find_replace_pairs = [(r"world(\d+)", r"universe\1"), (r"Python(\d+)", r"Programming\1")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs, use_regex=True)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello universe123, hello Programming456.")

    def test_find_and_replace_pairs__with_regex_special_chars(self):
        self.create_temp_file_with_content("Hello (world) [Python]")
        find_replace_pairs = [("(world)", "(universe)"), ("[Python]", "[Programming]")]
        result = find_and_replace_pairs(self.file_path, find_replace_pairs)
        self.assertEqual(result, 2)
        with open(self.file_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Hello (universe) [Programming]")

    def test_find_and_replace_pairs__with_metadata(self):
        complete_text = """## metadata
link: https://youtu.be/123456
note: test note


## content

Hello world
"""
        self.create_temp_file_with_content(complete_text)
        # Only match the base URL part, ignoring the video ID
        find_replace_pairs = [("link: https://youtu.be", "link youtube: https://youtu.be")]
        
        # Test with include_metadata=True (default)
        result = find_and_replace_pairs(self.file_path, find_replace_pairs, debug=True, include_metadata=True)
        
        # Add debug prints to see what read_file_flex returned
        metadata, content = read_file_flex(self.file_path)
        print(f"\nDebug - Metadata section being searched:\n'''{metadata}'''")
        print(f"Debug - Looking for pattern in metadata? {metadata and 'link: https://youtu.be' in metadata}")
        
        print(f"\nTest debug - Result: {result}")
        with open(self.file_path, 'r') as f:
            updated_text = f.read()
            print(f"Test debug - Updated text:\n'''{updated_text}'''")
        expected_text = """## metadata
link youtube: https://youtu.be/123456
note: test note


## content

Hello world
"""
        self.assertEqual(result, 1)
        self.assertEqual(updated_text, expected_text)
        
        # Test with include_metadata=False
        self.create_temp_file_with_content(complete_text)  # Reset text
        result = find_and_replace_pairs(self.file_path, find_replace_pairs, include_metadata=False)
        self.assertEqual(result, 0)
        with open(self.file_path, 'r') as f:
            unchanged_text = f.read()
        self.assertEqual(unchanged_text, complete_text)
class TestFindAndReplacePairsInFolder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder_path = self.temp_dir.name
        self.logs_folder = os.path.join(self.temp_dir.name, "logs", "find and replace logs")
        self.file1 = os.path.join(self.folder_path, "file1.txt")
        self.file2 = os.path.join(self.folder_path, "file2.md")
        self.subfolder = os.path.join(self.folder_path, "subfolder")
        self.subfolder_file = os.path.join(self.subfolder, "file3.txt")
        os.mkdir(self.subfolder)
    def tearDown(self):
        self.temp_dir.cleanup()
    def write_file(self, file_path, content):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
    def read_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    @patch('core.fileops.get_current_datetime_filefriendly', return_value='2026-03-26_123456')
    @patch('core.fileops._get_find_and_replace_logs_folder')
    def test_find_and_replace_pairs_in_folder__suffix_filter_and_log(self, mock_logs_folder, mock_timestamp):
        mock_logs_folder.return_value = self.logs_folder
        self.write_file(self.file1, "Alpha world\nBeta world")
        self.write_file(self.file2, "world should stay here")
        self.write_file(self.subfolder_file, "world should stay in subfolder")
        result = find_and_replace_pairs_in_folder(self.folder_path, [("world", "universe")], suffixpat_include='.txt', show_summary=False)
        self.assertEqual(result['files_scanned'], 1)
        self.assertEqual(result['total_replacements'], 2)
        self.assertIn(self.file1, result['files_changed'])
        self.assertEqual(result['files_changed'][self.file1]['total_replacements'], 2)
        self.assertEqual(self.read_file(self.file1), "Alpha universe\nBeta universe")
        self.assertEqual(self.read_file(self.file2), "world should stay here")
        self.assertEqual(self.read_file(self.subfolder_file), "world should stay in subfolder")
        self.assertEqual(result['log_file_path'], os.path.join(self.logs_folder, '2026-03-26_123456_find_and_replace_pairs_in_folder.md'))
        self.assertTrue(os.path.isfile(result['log_file_path']))
        log_text = self.read_file(result['log_file_path'])
        self.assertIn("files_changed: 1", log_text)
        self.assertIn("find: world | replace: universe | replacements: 2", log_text)
        self.assertIn("### file1.txt", log_text)
    @patch('core.fileops.get_current_datetime_filefriendly', return_value='2026-03-26_123457')
    @patch('core.fileops._get_find_and_replace_logs_folder')
    def test_find_and_replace_pairs_in_folder__include_subfolders_and_save_backups(self, mock_logs_folder, mock_timestamp):
        mock_logs_folder.return_value = self.logs_folder
        complete_text = """## metadata
world in metadata


## content

world in content
"""
        self.write_file(self.file1, complete_text)
        self.write_file(self.subfolder_file, "world in subfolder")
        result = find_and_replace_pairs_in_folder(self.folder_path, [("world", "universe")], suffixpat_include='.txt', include_subfolders=True, save_backups_of_changed_files=True, show_summary=False)
        self.assertEqual(result['files_scanned'], 2)
        self.assertEqual(result['total_replacements'], 2)
        self.assertTrue(result['backup_folder_path'].endswith('2026-03-26_123457_find_and_replace_backups'))
        backup_file1 = os.path.join(result['backup_folder_path'], 'file1.txt')
        backup_file2 = os.path.join(result['backup_folder_path'], 'subfolder', 'file3.txt')
        self.assertTrue(os.path.isfile(backup_file1))
        self.assertTrue(os.path.isfile(backup_file2))
        self.assertEqual(self.read_file(backup_file1), complete_text)
        self.assertEqual(self.read_file(backup_file2), "world in subfolder")
        self.assertEqual(self.read_file(self.file1), """## metadata
world in metadata


## content

universe in content
""")
        self.assertEqual(self.read_file(self.subfolder_file), "universe in subfolder")
        log_text = self.read_file(result['log_file_path'])
        self.assertIn("save_backups_of_changed_files: True", log_text)
        self.assertIn("### subfolder/file3.txt", log_text)
    @patch('builtins.input', return_value='n')
    @patch('core.fileops.get_current_datetime_filefriendly', return_value='2026-03-26_123458')
    @patch('core.fileops._get_find_and_replace_logs_folder')
    def test_find_and_replace_pairs_in_folder__prompt_reject_restores_original_file(self, mock_logs_folder, mock_timestamp, mock_input):
        mock_logs_folder.return_value = self.logs_folder
        original_text = "Keep world unchanged"
        self.write_file(self.file1, original_text)
        result = find_and_replace_pairs_in_folder(self.folder_path, [("world", "universe")], suffixpat_include='.txt', prompt_to_keep_updated_file=True, save_backups_of_changed_files=True, show_summary=False)
        self.assertEqual(result['total_replacements'], 0)
        self.assertEqual(result['files_changed'], {})
        self.assertIn(self.file1, result['files_rejected'])
        self.assertEqual(self.read_file(self.file1), original_text)
        backup_file = os.path.join(result['backup_folder_path'], 'file1.txt')
        self.assertTrue(os.path.isfile(backup_file))
        self.assertEqual(self.read_file(backup_file), original_text)
        log_text = self.read_file(result['log_file_path'])
        self.assertIn("files_rejected: 1", log_text)
        self.assertIn("## Rejected Changes", log_text)
        self.assertIn("### file1.txt", log_text)
    @patch('builtins.print')
    @patch('core.fileops.get_current_datetime_filefriendly', return_value='2026-03-26_123459')
    @patch('core.fileops._get_find_and_replace_logs_folder')
    def test_find_and_replace_pairs_in_folder__show_summary_default_prints_compact_report(self, mock_logs_folder, mock_timestamp, mock_print):
        mock_logs_folder.return_value = self.logs_folder
        self.write_file(self.file1, "world Python")
        self.write_file(self.subfolder_file, "world only")
        result = find_and_replace_pairs_in_folder(self.folder_path, [("world", "universe"), ("Python", "Programming")], suffixpat_include='.txt', include_subfolders=True)
        self.assertEqual(result['total_replacements'], 3)
        printed_lines = '\n'.join(call.args[0] for call in mock_print.call_args_list)
        self.assertIn("=== FIND AND REPLACE SUMMARY ===", printed_lines)
        self.assertIn(f"Files checked: {2}", printed_lines)
        self.assertIn("Find: 'world' -> Replace: 'universe'", printed_lines)
        self.assertIn("1 file1.txt", printed_lines)
        self.assertIn("1 subfolder/file3.txt", printed_lines)
        self.assertIn("Find: 'Python' -> Replace: 'Programming'", printed_lines)
        self.assertIn("1 file1.txt", printed_lines)
    @patch('builtins.print')
    @patch('core.fileops.get_current_datetime_filefriendly', return_value='2026-03-26_123460')
    @patch('core.fileops._get_find_and_replace_logs_folder')
    def test_find_and_replace_pairs_in_folder__show_summary_false_suppresses_summary_output(self, mock_logs_folder, mock_timestamp, mock_print):
        mock_logs_folder.return_value = self.logs_folder
        self.write_file(self.file1, "world")
        result = find_and_replace_pairs_in_folder(self.folder_path, [("world", "universe")], suffixpat_include='.txt', show_summary=False)
        self.assertEqual(result['total_replacements'], 1)
        mock_print.assert_not_called()

### HEADINGS
class TestGetHeadingLevel(unittest.TestCase):
    def test_get_heading_level__level_1(self):
        heading = "# Heading 1"
        result = get_heading_level(heading)
        self.assertEqual(result, 1)

    def test_get_heading_level__level_2(self):
        heading = "## Heading 2"
        result = get_heading_level(heading)
        self.assertEqual(result, 2)

    def test_get_heading_level__level_3(self):
        heading = "### Heading 3"
        result = get_heading_level(heading)
        self.assertEqual(result, 3)

    def test_get_heading_level__level_6(self):
        heading = "###### Heading 6"
        result = get_heading_level(heading)
        self.assertEqual(result, 6)

    def test_get_heading_level__no_heading(self):
        heading = "Not a heading"
        result = get_heading_level(heading)
        self.assertEqual(result, 0)

    def test_get_heading_level__empty_string(self):
        heading = ""
        result = get_heading_level(heading)
        self.assertEqual(result, 0)

    def test_get_heading_level__only_hash_symbols(self):
        heading = "####"
        result = get_heading_level(heading)
        self.assertEqual(result, 4)

    def test_get_heading_level__heading_with_spaces(self):
        heading = "#  Heading with spaces"
        result = get_heading_level(heading)
        self.assertEqual(result, 1)

    def test_get_heading_level__heading_with_leading_spaces(self):
        heading = "   ## Heading with leading spaces"
        result = get_heading_level(heading)
        self.assertEqual(result, 0)  # Expect 0 as headings shouldn't have leading spaces

class TestGetHeadingPattern(unittest.TestCase):
    def test_get_heading_pattern__basic_heading(self):
        heading = "# Heading 1"
        pattern = get_heading_pattern(heading)
        text = "# Heading 1\nSome content\n## Subheading\nMore content\n# Next Heading"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "# Heading 1\nSome content\n## Subheading\nMore content")

    def test_get_heading_pattern__subheading(self):
        heading = "## Heading 2"
        pattern = get_heading_pattern(heading)
        text = "# Main Heading\n## Heading 2\nSome content\n### Subheading\nMore content\n## Next Heading 2"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "## Heading 2\nSome content\n### Subheading\nMore content")

    def test_get_heading_pattern__deep_nested_headings(self):
        heading = "### Heading 3"
        pattern = get_heading_pattern(heading)
        text = "# H1\n## H2\n### Heading 3\nContent\n#### H4\nMore\n##### H5\nEven more\n### Next H3"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "### Heading 3\nContent\n#### H4\nMore\n##### H5\nEven more")

    def test_get_heading_pattern__no_match(self):
        heading = "# Non-existent Heading"
        pattern = get_heading_pattern(heading)
        text = "# Different Heading\nSome content\n## Subheading\nMore content"
        match = pattern.search(text)
        self.assertIsNone(match)

    def test_get_heading_pattern__end_of_document(self):
        heading = "# Last Heading"
        pattern = get_heading_pattern(heading)
        text = "# First Heading\nSome content\n# Last Heading\nFinal content"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "# Last Heading\nFinal content")

    def test_get_heading_pattern__empty_content(self):
        heading = "# Empty Heading"
        pattern = get_heading_pattern(heading)
        text = "# Previous Heading\nSome content\n# Empty Heading\n# Next Heading"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "# Empty Heading")

    def test_get_heading_pattern__special_characters(self):
        heading = "# Heading with (special) characters!"
        pattern = get_heading_pattern(heading)
        text = "# Normal Heading\n# Heading with (special) characters!\nContent here\n# Next Heading"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "# Heading with (special) characters!\nContent here")

    def test_get_heading_pattern__multiple_occurrences(self):
        heading = "## Repeated Heading"
        pattern = get_heading_pattern(heading)
        text = "# Main\n## Repeated Heading\nFirst occurrence\n# Other\n## Repeated Heading\nSecond occurrence"
        matches = list(pattern.finditer(text))
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].group().strip(), "## Repeated Heading\nFirst occurrence")
        self.assertEqual(matches[1].group().strip(), "## Repeated Heading\nSecond occurrence")

    def test_get_heading_pattern__multiline_content(self):
        heading = "# Multiline Heading"
        pattern = get_heading_pattern(heading)
        text = "# Multiline Heading\nLine 1\nLine 2\nLine 3\n# Next Heading"
        match = pattern.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group().strip(), "# Multiline Heading\nLine 1\nLine 2\nLine 3")

class TestFindHeadingText(unittest.TestCase):
    def test_find_heading_text__basic_heading(self):
        full_text = "# Heading 1\nSome content\n## Subheading\nMore content\n# Next Heading"
        heading = "# Heading 1"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "# Heading 1\nSome content\n## Subheading\nMore content\n")

    def test_find_heading_text__subheading(self):
        full_text = "# Main Heading\n## Heading 2\nSome content\n### Subheading\nMore content\n## Next Heading 2"
        heading = "## Heading 2"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "## Heading 2\nSome content\n### Subheading\nMore content\n")

    def test_find_heading_text__deep_nested_headings(self):
        full_text = "# H1\n## H2\n### Heading 3\nContent\n#### H4\nMore\n##### H5\nEven more\n### Next H3"
        heading = "### Heading 3"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "### Heading 3\nContent\n#### H4\nMore\n##### H5\nEven more\n")

    def test_find_heading_text__no_match(self):
        full_text = "# Different Heading\nSome content\n## Subheading\nMore content"
        heading = "# Non-existent Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNone(result)

    def test_find_heading_text__end_of_document(self):
        full_text = "# First Heading\nSome content\n# Last Heading\nFinal content"
        heading = "# Last Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "# Last Heading\nFinal content")

    def test_find_heading_text__empty_content(self):
        full_text = "# Previous Heading\nSome content\n# Empty Heading\n# Next Heading"
        heading = "# Empty Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "# Empty Heading\n")

    def test_find_heading_text__special_characters(self):
        full_text = "# Normal Heading\n# Heading with (special) characters!\nContent here\n# Next Heading"
        heading = "# Heading with (special) characters!"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "# Heading with (special) characters!\nContent here\n")

    def test_find_heading_text__multiple_occurrences(self):
        full_text = "# Main\n## Repeated Heading\nFirst occurrence\n# Other\n## Repeated Heading\nSecond occurrence"
        heading = "## Repeated Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "## Repeated Heading\nFirst occurrence\n")

    def test_find_heading_text__multiline_content(self):
        full_text = "# Multiline Heading\nLine 1\nLine 2\nLine 3\n# Next Heading"
        heading = "# Multiline Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "# Multiline Heading\nLine 1\nLine 2\nLine 3\n")

    def test_find_heading_text__empty_full_text(self):
        full_text = ""
        heading = "# Any Heading"
        result = find_heading_text(full_text, heading)
        self.assertIsNone(result)

    def test_find_heading_text__empty_heading(self):
        full_text = "# Some Heading\nContent"
        heading = ""
        result = find_heading_text(full_text, heading)
        self.assertIsNone(result)

    def test_find_heading_text__metadata_format2(self):
        full_text = "METADATA\nsome metadata content\nCONTENT\nsome content here"
        heading = "METADATA"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "METADATA\nsome metadata content\n")

    def test_find_heading_text__content_format2(self):
        full_text = "METADATA\nsome metadata content\nCONTENT\nsome content here"
        heading = "CONTENT"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:], "CONTENT\nsome content here")

    def test_find_heading_text__format2_no_content(self):
        full_text = "METADATA\nsome metadata content\n"
        heading = "CONTENT"
        result = find_heading_text(full_text, heading)
        self.assertIsNone(result)

    def test_find_heading_text__format2_no_metadata(self):
        full_text = "CONTENT\nsome content here"
        heading = "METADATA"
        result = find_heading_text(full_text, heading)
        self.assertIsNone(result)

    def test_find_heading_text__format2_empty_sections(self):
        full_text = "METADATA\nCONTENT\n"
        heading = "METADATA"
        result = find_heading_text(full_text, heading)
        self.assertIsNotNone(result)
        self.assertEqual(full_text[result[0]:result[1]], "METADATA\n")

class TestGetHeading(unittest.TestCase):
    def setUp(self):
        # Create a temporary test file
        self.test_filename = "test_heading_file.md"
        test_content = """
## Apple
This is the first heading's content.

## Banana
This is the second heading's content.

### Subheading under Banana
This is a subheading under the second heading.

## Coconut
This is the third heading's content.
"""
        with open(self.test_filename, 'w') as f:
            f.write(test_content)

        # Create a second test file for Format 2
        self.format2_filename = "test_format2_file.md"
        format2_content = """
METADATA
Some metadata content here.
More metadata.

CONTENT
Some content here.
More content.
"""
        with open(self.format2_filename, 'w') as f:
            f.write(format2_content)

    def tearDown(self):
        # Remove the temporary test files
        os.remove(self.test_filename)
        os.remove(self.format2_filename)

    def test_get_heading__valid_heading(self):
        # Test extraction of valid heading
        expected_content = "## Apple\nThis is the first heading's content.\n\n"
        self.assertEqual(get_heading(self.test_filename, "## Apple"), expected_content)

    def test_get_heading__subheading(self):
        # Test extraction of subheading
        expected_content = "### Subheading under Banana\nThis is a subheading under the second heading.\n\n"
        self.assertEqual(get_heading(self.test_filename, "### Subheading under Banana"), expected_content)

    def test_get_heading__double_heading_with_subheading(self):
        # Test extraction of heading with its subheading
        expected_content = """## Banana
This is the second heading's content.

### Subheading under Banana
This is a subheading under the second heading.

"""
        self.assertEqual(get_heading(self.test_filename, "## Banana"), expected_content)

    def test_get_heading__invalid_heading(self):
        # Test extraction of non-existent heading
        self.assertIsNone(get_heading(self.test_filename, "## Dragonfruit"))

    def test_get_heading__empty_file(self):
        # Test extraction from an empty file
        empty_filename = "empty_file.md"
        with open(empty_filename, 'w') as f:
            f.write("")
        self.assertIsNone(get_heading(empty_filename, "## Apple"))
        os.remove(empty_filename)

    def test_get_heading__strip_heading_line(self):
        # Test stripping the heading line
        expected_content = "This is the first heading's content.\n"  # Removed extra \n
        self.assertEqual(
            get_heading(self.test_filename, "## Apple", strip_heading_line=True),
            expected_content
        )

    def test_get_heading__strip_heading_line_with_subheading(self):
        # Test stripping heading line when there's a subheading
        expected_content = """This is the second heading's content.

### Subheading under Banana
This is a subheading under the second heading.\n"""  # Removed extra \n
        self.assertEqual(
            get_heading(self.test_filename, "## Banana", strip_heading_line=True),
            expected_content
        )

    def test_get_heading__format2_metadata(self):
        # Test extraction of METADATA section
        expected_content = """METADATA
Some metadata content here.
More metadata.

"""
        self.assertEqual(
            get_heading(self.format2_filename, "METADATA"),
            expected_content
        )

    def test_get_heading__format2_content(self):
        # Test extraction of CONTENT section
        expected_content = """CONTENT
Some content here.
More content.
"""
        self.assertEqual(
            get_heading(self.format2_filename, "CONTENT"),
            expected_content
        )

    def test_get_heading__format2_strip_heading(self):
        # Test stripping heading in Format 2
        expected_content = """Some metadata content here.
More metadata.\n"""  # Removed extra \n
        self.assertEqual(
            get_heading(self.format2_filename, "METADATA", strip_heading_line=True),
            expected_content
        )

class TestSetHeading(unittest.TestCase):
    def setUp(self):
        # Setup method to create a test file before each test case
        self.test_filename = 'test_heading_file.md'
        test_content = """## metadata
last updated: 2023-07-10


## content

### Heading 1
This is the first heading's content.

### Heading 2
This is the second heading's content.

#### Subheading 2.1
This is a subheading under heading 2.
"""
        with open(self.test_filename, 'w') as f:
            f.write(test_content)

    def tearDown(self):
        # Teardown method to remove test file after each test case
        os.remove(self.test_filename)

    def test_set_heading__replace_heading(self):
        # Test replacing the text of an existing heading
        new_text = "New content for heading 1.\n"
        set_heading(self.test_filename, new_text, "### Heading 1")
        _, content = read_metadata_and_content(self.test_filename)
        expected_text = "### Heading 1\nNew content for heading 1."
        self.assertIn(expected_text, content)
        self.assertNotIn("This is the first heading's content.", content)

    def test_set_heading__add_heading(self):
        # Test adding a new heading and its text
        new_text = "Content for the new heading.\n"
        set_heading(self.test_filename, new_text, "### New Heading")
        _, content = read_metadata_and_content(self.test_filename)
        expected_text = "### New Heading\nContent for the new heading."
        self.assertIn(expected_text, content)

    def test_set_heading__remove_heading(self):
        # Test removing the text of an existing heading
        set_heading(self.test_filename, "", "### Heading 2")
        _, content = read_metadata_and_content(self.test_filename)
        self.assertIn("### Heading 2", content)
        self.assertNotIn("This is the second heading's content.", content)

    def test_set_heading__add_heading_to_empty_content(self):
        # Test adding a heading to empty content
        with open(self.test_filename, 'w') as f:
            f.write("## metadata\n\n## content\n")
        new_text = "New content.\n"
        set_heading(self.test_filename, new_text, "### New Heading")
        _, content = read_metadata_and_content(self.test_filename)
        expected_text = "## content\n\n### New Heading\nNew content."
        self.assertEqual(content, expected_text)

    def test_set_heading__metadata_preserved(self):
        # Test that metadata is preserved when setting a heading
        new_text = "New content.\n"
        set_heading(self.test_filename, new_text, "### New Heading")
        metadata, content = read_metadata_and_content(self.test_filename)
        self.assertIn("## metadata", metadata)
        self.assertIn("last updated: 2023-07-10", metadata)

    def test_set_heading__no_duplicate_heading(self):
        # Test that setting text that already includes the heading doesn't duplicate it
        new_text = "### Heading 1\nNew content for heading 1.\n"
        set_heading(self.test_filename, new_text, "### Heading 1")
        _, content = read_metadata_and_content(self.test_filename)
        self.assertEqual(content.count("### Heading 1"), 1)  # Should only appear once

class TestDeleteHeading(unittest.TestCase):
    def setUp(self):
        # Setup method to create a test file before each test case
        self.test_filename = 'test_heading_file.md'
        test_content = """## metadata
last updated: 2023-07-10

## content

### Heading 1
This is the first heading's content.

### Heading 2
This is the second heading's content.

#### Subheading 2.1
This is a subheading under heading 2.
"""
        with open(self.test_filename, 'w') as f:
            f.write(test_content)

    def tearDown(self):
        # Teardown method to remove test file after each test case
        os.remove(self.test_filename)

    def test_delete_heading__delete_existing_heading(self):
        # Test deleting an existing heading and its text
        delete_heading(self.test_filename, "### Heading 1")
        _, content = read_metadata_and_content(self.test_filename)
        self.assertNotIn("### Heading 1", content)
        self.assertNotIn("This is the first heading's content.", content)
        self.assertIn("### Heading 2", content)  # Ensure other headings are preserved

    def test_delete_heading__delete_nonexistent_heading(self):
        # Test deleting a nonexistent heading (should not modify the file)
        original_content = read_complete_text(self.test_filename)
        with self.assertWarns(UserWarning):
            delete_heading(self.test_filename, "### Nonexistent Heading")
        new_content = read_complete_text(self.test_filename)
        self.assertEqual(original_content, new_content)

    def test_delete_heading__preserve_metadata(self):
        # Test that metadata is preserved when deleting a heading
        delete_heading(self.test_filename, "### Heading 1")
        metadata, _ = read_metadata_and_content(self.test_filename)
        self.assertIn("## metadata", metadata)
        self.assertIn("last updated: 2023-07-10", metadata)

    def test_delete_heading__delete_heading_with_subheadings(self):
        # Test deleting a heading that has subheadings
        delete_heading(self.test_filename, "### Heading 2")
        _, content = read_metadata_and_content(self.test_filename)
        self.assertNotIn("### Heading 2", content)
        self.assertNotIn("This is the second heading's content.", content)
        self.assertNotIn("#### Subheading 2.1", content)
        self.assertNotIn("This is a subheading under heading 2.", content)

    def test_delete_heading__delete_last_heading(self):
        # Test deleting the last heading in the file
        delete_heading(self.test_filename, "#### Subheading 2.1")
        _, content = read_metadata_and_content(self.test_filename)
        self.assertIn("### Heading 2", content)
        self.assertNotIn("#### Subheading 2.1", content)
        self.assertNotIn("This is a subheading under heading 2.", content)

class TestAppendHeadingToFile(unittest.TestCase):
    def setUp(self):
        # Create a temporary source file
        self.source_file = tempfile.NamedTemporaryFile(delete=False)
        self.source_file_path = self.source_file.name
        self.source_content = """## Header
### summaries
This is the summaries section.
Another line of summaries."""
        self.source_file.write(self.source_content.encode())
        self.source_file.close()

        # Create a temporary target file
        self.target_file = tempfile.NamedTemporaryFile(delete=False)
        self.target_file_path = self.target_file.name
        self.target_file.close()

    def tearDown(self):
        # Remove the temporary files after each test
        os.remove(self.source_file_path)
        os.remove(self.target_file_path)

    def test_append_heading_to_file__include_filename(self):
        # Append the heading to the target file and include the filename
        heading = "### summaries"
        append_heading_to_file(self.source_file_path, self.target_file_path, heading, include_filename=True)
        
        # Verify the content of the target file
        with open(self.target_file_path, 'r') as file:
            content = file.read()

        expected_heading_level = "##"  # One level less than the heading in the source content
        filename_heading = f"{expected_heading_level} {os.path.basename(self.source_file_path)}"
        expected_content = f"{filename_heading}\n{heading}\nThis is the summaries section.\nAnother line of summaries."
        self.assertIn(expected_content, content)

    def test_append_heading_to_file__without_include_filename(self):
        # Append the heading to the target file without including the filename
        heading = "### summaries"
        append_heading_to_file(self.source_file_path, self.target_file_path, heading, include_filename=False)
        
        # Verify the content of the target file
        with open(self.target_file_path, 'r') as file:
            content = file.read()

        expected_content = f"{heading}\nThis is the summaries section.\nAnother line of summaries."
        self.assertIn(expected_content, content)

class TestCreateNewFileFromHeading(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.original_file_path = os.path.join(self.test_dir.name, 'testfile.md')
        self.content = """
# Main Header
Content under the main heading
## Subheading 1
Content under subheading 1
### Your Heading
Content under your heading
#### Subheading 1
Sub content under your heading
##### Subheading 2
More sub content
### Another Heading

Content under another heading
"""
        with open(self.original_file_path, 'w') as file:
            file.write(self.content)

    def tearDown(self):
        self.test_dir.cleanup()

    @patch('core.fileops.get_heading')
    @patch('core.fileops.write_complete_text')
    def test_create_new_file_from_heading__basic_functionality(self, mock_write, mock_get_heading):
        mock_get_heading.return_value = "### Your Heading\nContent under your heading\n"
        mock_write.return_value = "new_file_path.md"

        result = create_new_file_from_heading(self.original_file_path, "### Your Heading")

        mock_get_heading.assert_called_once_with(self.original_file_path, "### Your Heading")
        mock_write.assert_called_once_with(self.original_file_path, "Content under your heading\n", "_headingonly")
        self.assertEqual(result, "new_file_path.md")

    @patch('core.fileops.get_heading')
    @patch('core.fileops.write_complete_text')
    def test_create_new_file_from_heading__custom_suffix(self, mock_write, mock_get_heading):
        mock_get_heading.return_value = "### Your Heading\nContent under your heading\n"
        mock_write.return_value = "new_file_path.md"

        result = create_new_file_from_heading(self.original_file_path, "### Your Heading", "_custom")

        mock_write.assert_called_once_with(self.original_file_path, "Content under your heading\n", "_custom")

    @patch('core.fileops.get_heading')
    @patch('core.fileops.write_complete_text')
    def test_create_new_file_from_heading__multiple_lines(self, mock_write, mock_get_heading):
        mock_get_heading.return_value = "### Your Heading\nLine 1\nLine 2\nLine 3\n"
        mock_write.return_value = "new_file_path.md"

        result = create_new_file_from_heading(self.original_file_path, "### Your Heading")

        mock_write.assert_called_once_with(self.original_file_path, "Line 1\nLine 2\nLine 3\n", "_headingonly")

    @patch('core.fileops.get_heading')
    @patch('core.fileops.write_complete_text')
    def test_create_new_file_from_heading__nonexistent_heading(self, mock_write, mock_get_heading):
        mock_get_heading.return_value = None
        mock_write.return_value = "new_file_path.md"

        result = create_new_file_from_heading(self.original_file_path, "### Nonexistent Heading")

        mock_write.assert_called_once_with(self.original_file_path, "", "_headingonly")
        self.assertEqual(result, "new_file_path.md")

    @patch('core.fileops.get_heading')
    @patch('core.fileops.write_complete_text')
    def test_create_new_file_from_heading__empty_file(self, mock_write, mock_get_heading):
        mock_get_heading.return_value = None
        mock_write.return_value = "new_file_path.md"

        result = create_new_file_from_heading(self.original_file_path, "### Your Heading")

        mock_write.assert_called_once_with(self.original_file_path, "", "_headingonly")
        self.assertEqual(result, "new_file_path.md")

    def test_create_new_file_from_heading__integration(self):
        result = create_new_file_from_heading(self.original_file_path, "### Your Heading")
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as new_file:
            content = new_file.read()
            expected_content = ("Content under your heading\n"
                                "#### Subheading 1\n"
                                "Sub content under your heading\n"
                                "##### Subheading 2\n"
                                "More sub content\n")
            self.assertEqual(content, expected_content)

    def test_create_new_file_from_heading__integration_nonexistent_heading(self):
        result = create_new_file_from_heading(self.original_file_path, "### Nonexistent Heading")
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as new_file:
            content = new_file.read()
            self.assertEqual(content, "")  # Expect an empty file when heading doesn't exist

    def test_create_new_file_from_heading__integration_empty_file(self):
        empty_file_path = os.path.join(self.test_dir.name, 'empty.md')
        with open(empty_file_path, 'w') as file:
            pass  # create an empty file
        
        result = create_new_file_from_heading(empty_file_path, "### Your Heading")
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as new_file:
            content = new_file.read()
            self.assertEqual(content, "")  # Expect an empty file when source file is empty

    def test_create_new_file_from_heading__remove_heading_no_blank_line(self):
        result = create_new_file_from_heading(self.original_file_path, "### Your Heading", remove_heading=True)
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as new_file:
            content = new_file.read()
            expected_content = ("Content under your heading\n"
                                "#### Subheading 1\n"
                                "Sub content under your heading\n"
                                "##### Subheading 2\n"
                                "More sub content\n")
            self.assertEqual(content, expected_content)

    def test_create_new_file_from_heading__remove_heading_with_blank_line(self):
        result = create_new_file_from_heading(self.original_file_path, "### Another Heading", remove_heading=True)
        
        self.assertTrue(os.path.exists(result))
        with open(result, 'r') as new_file:
            content = new_file.read()
            expected_content = "Content under another heading\n"
            self.assertEqual(content, expected_content)

class TestCreateCSVFromFields(unittest.TestCase):
    def setUp(self):
        # Setup a temporary directory
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def test_create_csv_from_fields__header_pattern(self):
        """ Test basic CSV file creation and header pattern """
        # Create a temporary markdown file
        md_content = "#header pattern\nThis is a test markdown file.\nLine2\nLine3"
        md_file_path = os.path.join(self.temp_dir.name, "test.md")
        with open(md_file_path, 'w') as md_file:
            md_file.write(md_content)

        # Call the function
        csv_path = create_csv_from_fields(self.temp_dir.name, ["#header pattern"])
        
        # Check if CSV file is created and contains expected data
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            lines = list(reader)
            self.assertEqual(len(lines), 2)  # header and one data row
            self.assertEqual(lines[0], ['file_name', 'title', 'header pattern'])
            self.assertEqual(lines[1], ['test.md', 'test', 'This is a test markdown file.\nLine2\nLine3'])

    def test_create_csv_from_fields__metadata_pattern(self):
        """ Test basic CSV file creation and metadata pattern """
        # Create a temporary markdown file
        md_content = "metadata pattern:\nThis is a test markdown file.\nLine2\nLine3"
        md_file_path = os.path.join(self.temp_dir.name, "test.md")
        with open(md_file_path, 'w') as md_file:
            md_file.write(md_content)

        # Call the function
        csv_path = create_csv_from_fields(self.temp_dir.name, ["metadata pattern:"])
        
        # Check if CSV file is created and contains expected data
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            lines = list(reader)
            self.assertEqual(len(lines), 2)  # header and one data row
            self.assertEqual(lines[1], ['test.md', 'test', 'This is a test markdown file.'])

    def test_create_csv_from_fields__two_metadata_fields(self):
        """ Test CSV file creation with two specified metadata fields """
        # Create a temporary markdown file with content matching two fields
        md_content = "Title:\nContent that should be extracted.\nAnotherTitle:\nLine1 Subtitle\n"
        md_file_path = os.path.join(self.temp_dir.name, "test.md")
        with open(md_file_path, 'w') as md_file:
            md_file.write(md_content)
    
        # Call the function
        csv_path = create_csv_from_fields(self.temp_dir.name, ["Title:", "AnotherTitle:"])
        
        # Check if CSV file is created and contains expected data
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            lines = list(reader)
            # Check headers and data rows
            self.assertEqual(lines[0], ['file_name', 'title', 'Title', 'AnotherTitle'])
            self.assertEqual(lines[1], ['test.md', 'test', 'Content that should be extracted.', 'Line1 Subtitle'])

    @patch("builtins.input", side_effect=["n"])
    def test_create_csv_from_fields__existing_file_no_overwrite(self, mock_input):
        """ Test handling of existing CSV file when user decides not to overwrite """
        # Create a CSV file in the temp directory
        existing_csv_path = os.path.join(self.temp_dir.name, self.temp_dir.name + ".csv")
        with open(existing_csv_path, "w") as f:
            f.write("Header\n")

        # Call the function
        csv_path = create_csv_from_fields(self.temp_dir.name, [])

        # Check if a new CSV file is created
        self.assertNotEqual(existing_csv_path, csv_path)
        self.assertTrue(os.path.exists(csv_path))

    def test_create_csv_from_fields__permission_error(self):
        """ Test handling of permission errors during CSV file writing """
        # Set folder to non-writable (simulating permission error)
        os.chmod(self.temp_dir.name, 0o400)  # Read-only
        try:
            with self.assertRaises(PermissionError) as context:
                create_csv_from_fields(self.temp_dir.name, [])
        finally:
            # Restore permissions for cleanup
            os.chmod(self.temp_dir.name, 0o700)
            self.assertIn("Permission denied", str(context.exception))

class TestCreateCSVMatrixFromTriples(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_csv_matrix_from_triples__basic_functionality(self):
        triples_text = "Row1, Col1, 100\nRow2, Col2, 200"
        target_path = os.path.join(self.temp_dir.name, "output.csv")
        result_path = create_csv_matrix_from_triples(triples_text, target_path)
        self.assertEqual(result_path, target_path)
        with open(result_path, 'r') as file:
            reader = list(csv.reader(file))
            expected = [['row title', 'Col1', 'Col2'], ['Row1', '100', '0'], ['Row2', '0', '200']]
            self.assertEqual(reader, expected)

    def test_create_csv_matrix_from_triples__incorrect_format_raises_error(self):
        triples_text = "Row1, Col1\nRow2, Col2, 200"
        target_path = os.path.join(self.temp_dir.name, "output.csv")
        with self.assertRaises(ValueError):
            create_csv_matrix_from_triples(triples_text, target_path)

    def test_create_csv_matrix_from_triples__empty_input(self):
        triples_text = ""
        target_path = os.path.join(self.temp_dir.name, "output.csv")
        result_path = create_csv_matrix_from_triples(triples_text, target_path)
        with open(result_path, 'r') as file:
            reader = list(csv.reader(file))
            self.assertEqual(reader, [['row title']])


### METADATA
class TestSetMetadataField(unittest.TestCase):
    def test_set_metadata_field__add_new_field(self):
        header = "## metadata\n\n## content\n\n"
        field = "length"
        value = "4:30"
        expected_header = "## metadata\nlength: 4:30\n\n## content\n\n"
        updated_header = set_metadata_field(header, field, value)
        self.assertEqual(updated_header, expected_header)

    def test_set_metadata_field__update_existing_field(self):
        header = "## metadata\nlast updated: old_value\n\n## content\n\n"
        field = "last updated"
        value = "11-19-2023 by Susan"
        expected_header = "## metadata\nlast updated: 11-19-2023 by Susan\n\n## content\n\n"
        updated_header = set_metadata_field(header, field, value)
        self.assertEqual(updated_header, expected_header)

    def test_set_metadata_field__add_two_fields(self):
        header = "## metadata\nlast updated: old_value\n\n## content\n\n"
        field1 = "last updated"
        value1 = "11-19-2023 by Susan"
        field2 = "link"
        value2 = "dummy"
        expected_header = "## metadata\nlast updated: 11-19-2023 by Susan\nlink: dummy\n\n## content\n\n"
        updated_header = set_metadata_field(header, field1, value1)
        updated_header = set_metadata_field(updated_header, field2, value2)
        self.assertEqual(updated_header, expected_header)

    def test_set_metadata_field__add_field_when_no_blank_line_at_header_end(self):
        # We should only pass the metadata section to set_metadata_field
        metadata = "## metadata"  # Just the metadata section
        field = "new_field"
        value = "new_value"
        expected_metadata = "## metadata\nnew_field: new_value"
        updated_metadata = set_metadata_field(metadata, field, value)
        self.assertEqual(updated_metadata, expected_metadata)

class TestRemoveMetadataField(unittest.TestCase):
    def test_remove_metadata_field__existing_field(self):
        header = "## metadata\nlength: 4:30\nlast updated: 11-19-2023 by Susan\n\n## content\n\n"
        field = "length"
        expected_header = "## metadata\nlast updated: 11-19-2023 by Susan\n\n## content\n\n"
        updated_header = remove_metadata_field(header, field)
        self.assertEqual(updated_header, expected_header)

    def test_remove_metadata_field__nonexistent_field(self):
        header = "## metadata\nlength: 4:30\n\n## content\n\n"
        field = "nonexistent"
        expected_header = "## metadata\nlength: 4:30\n\n## content\n\n"
        updated_header = remove_metadata_field(header, field)
        self.assertEqual(updated_header, expected_header)

    def test_remove_metadata_field__multiple_fields(self):
        header = "## metadata\nlength: 4:30\nlast updated: 11-19-2023 by Susan\n\n## content\n\n"
        field = "last updated"
        expected_header = "## metadata\nlength: 4:30\n\n## content\n\n"
        updated_header = remove_metadata_field(header, field)
        self.assertEqual(updated_header, expected_header)

class TestSetLastUpdated(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, 'test_file.md')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_set_last_updated__add_new_field(self):
        # Create file with metadata but no last updated field
        initial_content = "## metadata\n\n\n## content\n\nThis here.\n"
        with open(self.test_file, 'w') as f:
            f.write(initial_content)

        new_value = "by John"
        date_today = datetime.now().strftime("%m-%d-%Y")
        expected_content = f"## metadata\nlast updated: {date_today} by John\n\n\n## content\n\nThis here.\n"
        
        set_last_updated(self.test_file, new_value)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertEqual(content, expected_content)

    def test_set_last_updated__update_existing_field(self):
        # Create file with existing last updated field
        initial_content = "## metadata\nlast updated: old_value\n\n\n## content\n\nThis here.\n"
        with open(self.test_file, 'w') as f:
            f.write(initial_content)

        new_value = "by Susan"
        date_today = datetime.now().strftime("%m-%d-%Y")
        expected_content = f"## metadata\nlast updated: {date_today} by Susan\n\n\n## content\n\nThis here.\n"
        
        set_last_updated(self.test_file, new_value)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertEqual(content, expected_content)

    def test_set_last_updated__prepend_today_false(self):
        # Create file with existing last updated field
        initial_content = "## metadata\nlast updated: old_value\n\n## content\n\nThis here.\n"
        with open(self.test_file, 'w') as f:
            f.write(initial_content)

        new_value = "11-19-2023 by Susan"
        expected_content = "## metadata\nlast updated: 11-19-2023 by Susan\n\n\n## content\n\nThis here.\n"
        
        set_last_updated(self.test_file, new_value, prepend_today=False)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertEqual(content, expected_content)

    def test_set_last_updated__nonexistent_file(self):
        # Test handling of non-existent file
        nonexistent_file = os.path.join(self.temp_dir.name, 'nonexistent.md')
        with self.assertRaises(ValueError):
            set_last_updated(nonexistent_file, "by John")

    def test_set_last_updated__preserve_content(self):
        # Test that existing content is preserved
        original_content = "## metadata\n\n## content\nSome important content\nMore content\n"
        with open(self.test_file, 'w') as f:
            f.write(original_content)

        new_value = "by John"
        set_last_updated(self.test_file, new_value)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertIn("Some important content", content)
            self.assertIn("More content", content)

class TestSetMetadataFieldsFromCSV(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to simulate the folder containing files
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create a sample CSV file for testing
        self.csv_file_path = os.path.join(self.temp_dir.name, "metadata.csv")
        with open(self.csv_file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['filename', 'author', 'revision'])
            writer.writerow(['document1', 'John Doe', '1'])
            writer.writerow(['document2', 'Jane Smith', '2'])

        # Create sample files mentioned in the CSV
        self.file_paths = [
            os.path.join(self.temp_dir.name, 'document1.md'),
            os.path.join(self.temp_dir.name, 'document2.md')
        ]
        for file_path in self.file_paths:
            with open(file_path, 'w') as f:
                f.write("## metadata\nlast updated: \n\n## content\n\nInitial content")

    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    def test_set_metadata_fields_from_csv__basic_functionality(self):
        set_metadata_fields_from_csv(self.temp_dir.name, self.csv_file_path, '.md')
        # Check if the files were updated correctly
        with open(self.file_paths[0], 'r') as f:
            content = f.read()
            self.assertIn('author: John Doe', content)
            self.assertIn('revision: 1', content)

    def test_set_metadata_fields_from_csv__insufficient_columns(self):
        # Alter the CSV to have insufficient columns in one row
        with open(self.csv_file_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['document3'])  # No additional columns provided

        # Run the function
        set_metadata_fields_from_csv(self.temp_dir.name, self.csv_file_path, '.md')
        # No actual checks are performed as we expect print statements indicating the issue

    def test_set_metadata_fields_from_csv__non_existent_file(self):
        # Include a non-existent file in the CSV
        with open(self.csv_file_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['document3', 'Unknown Author', '3'])

        # Run the function
        set_metadata_fields_from_csv(self.temp_dir.name, self.csv_file_path, '.md')
        # No actual checks are performed as we expect print statements indicating the issue


### JSON
class TestPrettyPrintJsonStructure(unittest.TestCase):
    def setUp(self):
        # Create a temporary JSON file
        self.temp_json_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json')
        self.test_json_data = {
            "key1": "value1",
            "key2": ["list_item1", "list_item2"],
            "key3": {
                "subkey1": "subvalue1"
            }
        }
        json.dump(self.test_json_data, self.temp_json_file)
        self.temp_json_file.close()

    def tearDown(self):
        # Clean up by removing the temporary file and its '.pretty' counterpart
        os.unlink(self.temp_json_file.name)
        if os.path.exists(self.temp_json_file.name + '.pretty'):
            os.unlink(self.temp_json_file.name + '.pretty')

    def test_pretty_print_json_file__with_save(self):
        # Test that the output is correctly saved to a '.pretty' file
        pretty_print_json_file(self.temp_json_file.name, level_limit=2, save_to_file=True)
        pretty_file_path = self.temp_json_file.name + '.pretty'
        self.assertTrue(os.path.exists(pretty_file_path))

    def test_pretty_print_json_file__level_limit(self):
        # Test the level limit functionality by inspecting the saved file content
        # (This test assumes that examining the saved file's content can indirectly verify the level limit functionality)
        pretty_print_json_file(self.temp_json_file.name, level_limit=1, save_to_file=True)
        pretty_file_path = self.temp_json_file.name + '.pretty'
        with open(pretty_file_path, 'r') as pretty_file:
            contents = pretty_file.readlines()
            # Verify that contents respect the level limit (exact verification depends on function's output format)
            self.assertTrue(any("key3" in line for line in contents))
            # This checks if 'key3' is present but does not verify deeper structures beyond the level limit

    def test_pretty_print_json_file__without_save(self):
        # Test that the output is not saved to a file when save_to_file is False
        pretty_print_json_file(self.temp_json_file.name, level_limit=2, save_to_file=False)
        pretty_file_path = self.temp_json_file.name + '.pretty'
        self.assertFalse(os.path.exists(pretty_file_path))

    def test_pretty_print_json_file__no_level_limit(self):
        # Test that all levels are printed when level_limit is None
        pretty_print_json_file(self.temp_json_file.name, level_limit=None, save_to_file=True)
        pretty_file_path = self.temp_json_file.name + '.pretty'
        with open(pretty_file_path, 'r') as pretty_file:
            contents = pretty_file.read()
            # Verify that all levels are printed (exact verification depends on function's output format)
            self.assertIn("subkey1", contents)

    def test_pretty_print_json_file__with_nonexistent_file(self):
        # Test that a warning is raised when the file does not exist
        non_existent_file_path = "non_existent_file.json"
        with self.assertWarns(Warning):
            pretty_print_json_file(non_existent_file_path, level_limit=2, save_to_file=True)

    def test_pretty_print_json_file__save_to_file_false(self):
        # Test pretty printing JSON structure without saving to file
        json_file_path = self.temp_json_file.name
        pretty_print_json_file(json_file_path, level_limit=2, save_to_file=False)

        output_file_path = json_file_path + '.pretty'
        self.assertFalse(os.path.exists(output_file_path), "Output file should not exist when save_to_file is False.")

    def test_pretty_print_json_file__non_existent_file(self):
        # Test handling of non-existent JSON file
        non_existent_file_path = 'non_existent_file.json'
        with self.assertWarns(Warning) as warning:
            pretty_print_json_file(non_existent_file_path)
        self.assertIn("does not exist", str(warning.warning.args[0]), "Warning should mention the non-existent file.")

    def test_pretty_print_json_file__no_level_limit(self):
        # Test printing JSON structure without a level limit
        json_file_path = self.temp_json_file.name
        pretty_print_json_file(json_file_path, level_limit=None, save_to_file=False)

        # Verifying the function runs without error and the precise output check is done through inspection

    def test_pretty_print_json_file__specific_level_limit(self):
        # Test printing JSON structure with a specific level limit
        json_file_path = self.temp_json_file.name
        pretty_print_json_file(json_file_path, level_limit=1, save_to_file=False)

        # This test ensures that the function correctly limits the printing depth
        # Precise output verification is manual due to the nature of console output

    def test_pretty_print_json_file__empty_json(self):
        # Test handling of an empty JSON file
        empty_json_file_path = tempfile.mkstemp(suffix='.json')[1]
        with open(empty_json_file_path, 'w') as file:
            json.dump({}, file)


# AssertionError: 'Returned' != 'Expected'

if __name__ == '__main__':
    unittest.main()