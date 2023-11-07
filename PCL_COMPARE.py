import subprocess
import re

# The path to the C++ executable
PCL_EXE_PATH = "C:\\Users\\mcitrin\\Documents\\Submodule_Test\\build\\submodules\\Release\\PointCloudComparisonMain.exe"

def PCL_COMPARE_2_VMTK(json_path, vtk_path):
    # Call the executable using subprocess
    process = subprocess.Popen([PCL_EXE_PATH, json_path, vtk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Wait for the process to complete and capture the output and error (if any)
    stdout, stderr = process.communicate()

    # Check for errors
    if process.returncode != 0:
        print(f"An error occurred: {stderr}")
    else:
        # Use a regular expression to find the line with the score
        match = re.search(r'SCORE:(\d+(\.\d+)?)$', stdout, re.MULTILINE)
        if match:
            # Extract the score (as a string)
            score_str = match.group(1)
            # Convert the score to a float
            try:
                score = float(score_str)
                print(f"The C++ program returned the score: {score}")
                return score
            except ValueError as e:
                print(f"Could not convert score to float: {score_str}")
        else:
            print("No line with 'SCORE:' found in the output.")
    return 1e+10