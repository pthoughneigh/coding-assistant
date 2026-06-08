import subprocess
from config import WORKSPACE_PATH


def read_file(file_name: str) -> str:
    """
    Read and return the contents of a file from the workspace.

    Args:
        file_name: Path to the file relative to WORKSPACE_PATH.

    Returns:
        The file contents as a UTF-8 string, or an error message if the file
        could not be read. Error messages begin with 'Error:' and describe
        the failure so the agent can decide how to proceed.

    Raises:
        Nothing — all exceptions are caught and returned as error strings.
    """
    path = WORKSPACE_PATH / file_name
    try:
        with open(path, 'r', encoding='utf-8') as file:
            file_content = file.read()
            return file_content
    except FileNotFoundError:
        return f'Error: File {file_name} does not exist in {WORKSPACE_PATH}'
    except PermissionError:
        return f"Error: insufficient permissions to read '{file_name}'"
    except IsADirectoryError:
        return f"Error: '{file_name}' is a directory, not a file"
    except UnicodeDecodeError:
        return f"Error: '{file_name}' could not be decoded as UTF-8 — may be a binary file"
    except OSError as e:
        return f"Error: could not read '{file_name}' — {e}"
    

def write_file(file_name: str, file_content: str) -> str:
    """
    Takes a filename and the full new content as a string, and overwrites the file.
    
    Args:
        file_name: Path to the file relative to WORKSPACE_PATH.
        file_content: Raw text - new content for a file.

    Returns:
        A success message if the file was written, or an error message if it
        could not be written. Error messages begin with 'Error:' and describe
        the failure so the agent can decide how to proceed.

    Raises:
        Nothing — all exceptions are caught and returned as error strings.
    """
    path = WORKSPACE_PATH / file_name
    try:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(file_content)
            return f"Successfully wrote '{file_name}'"
    except FileNotFoundError:
        return f"Error: directory for '{file_name}' does not exist"
    except PermissionError:
        return f"Error: insufficient permissions to write '{file_name}'"
    except IsADirectoryError:
        return f"Error: '{file_name}' is a directory, not a file"
    except UnicodeEncodeError:
        return f"Error: '{file_name}' could not be decoded as UTF-8 — may be a binary file"
    except OSError as e:
        return f"Error: could not write to '{file_name}' — {e}"
    

def run_tests(file_name: str) -> str:
    """
    Run pytest on a file and return the result.

    Args:
        file_name: Path to the test file relative to WORKSPACE_PATH.

    Returns:
        A string containing the test result, stdout output, and stderr output.
        The result is a human-readable interpretation of pytest's return code.
        Error messages begin with 'Error:' and describe the failure so the
        agent can decide how to proceed.

    Raises:
        Nothing — all exceptions are caught and returned as error strings.
    """
    codes = {0: 'passed', 1: 'tests failed', 2: 'interrupted', 3: 'internal error', 4: 'usage error', 5: 'no tests found'}
    try:
        sb = subprocess.run(['pytest', str(WORKSPACE_PATH / file_name)], capture_output=True, encoding='utf-8')
        code_meaning = codes.get(sb.returncode, 'unknown')
        return f"Result: {code_meaning}\nOutput:\n{sb.stdout}\nErrors:\n{sb.stderr}"
    except FileNotFoundError:
        return "Error: pytest is not installed or not on PATH"
    except PermissionError:
        return f"Error: insufficient permissions to run tests on '{file_name}'"
    except OSError as e:
        return f"Error: could not run tests on '{file_name}' — {e}"
    

def search_code(pattern: str) -> str:
    """
    Search all files in the workspace for lines matching a pattern.

    Args:
        pattern: String to search for in file contents.

    Returns:
        A formatted string of matched file paths and their matching lines,
        or a message indicating no matches were found. Error messages begin
        with 'Error:' and describe the failure so the agent can decide how
        to proceed. Files that cannot be decoded as UTF-8 are skipped silently.

    Raises:
        Nothing — all exceptions are caught and returned as error strings.
    """
    search_result = f"No matches for '{pattern}' found in '{WORKSPACE_PATH}'"
    matches = []
    try:
        for path in WORKSPACE_PATH.rglob('*'):
            if path.is_file():
                try: 
                    content = path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    continue
                lines = [line for line in content.splitlines() if pattern in line]
                if lines:
                    matches.append({'file': str(path), 'lines': lines})
    
    except PermissionError:
        return f"Error: insufficient permissions to search '{WORKSPACE_PATH}'"
    except OSError as e:
        return f"Error: could not search '{WORKSPACE_PATH}' — {e}"
    
    if matches:
        search_result = "\n".join(f"Path: {m['file']}\n{'\n'.join(m['lines'])}" for m in matches)

    return search_result