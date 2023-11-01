import os
import fnmatch
import time
import subprocess
import json
import shutil
import nni
import SKJson2VTk

# Constants
OUTPUT_DIR = "."
INPUT_STL_DIR = "C:\\Users\\mcitrin\\Documents\\AAA_Sekeletonization_Error\\TEST_STLS"
EXPERIMENT_NAME = "NNI_TEST_NEW_SCRIPT2"
SEARCH_SPACE_JSON = "C:\\Users\\mcitrin\\Documents\\python_scripts\\AAA_NNI\\Skeletonization\\search_space.json"
SKELETONIZE_EXE = "C:\\Users\\mcitrin\\Documents\\Submodule_Test\\build\\submodules\\Release\\SK_Lite.exe"
SKETLTON_TIMEOUT = 180

# Skeleton json keys
vertices_key = 'SurfaceMeshVertices'
faces_key = 'SurfaceMeshFaces'
sk_points_key = 'SkPoints'
edges_key = 'SkEdges'
polylines_key = 'Polylines'


# Default parameters for input file
DEFAULT_PARAMETERS = {
    "MaxTriangleAngle": "110.0",
    "QualitySpeedTradeoff": "0.5",
    "MedialSpeedTradeoff": "1.5",
    "AreaVariationFactor": "0.0001",
    "MaxIterations": "600",
    "MinEdgeLength": "0.065",
    "RunMetrics": "0",
    "DebugPopups": "0",
    "UseInletPopup": "0",
    "UseNeckPlane": "0",
}

# dictonary for computed metrics of a trial
TRIAL_METRICS = {
    "passed":0,
    "bifurcations": 0,
    "termina": 0,
    "avg_degree": 0,
    "skeleton_length": 0,
    "total_time": 0
}

def Mkdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def LowerFnmatch(haystack, needle):
    return fnmatch.fnmatch(haystack.lower(), needle.lower())     
# return the full path to file that has the tag attached to its file name.
def findFile(search_dir, TAG):
    if os.path.isdir(search_dir):
      for root, dirs, files in os.walk(search_dir):
        for name in files:
            if LowerFnmatch(name, TAG):
                return os.path.join(root, name)
    return 'NULL'

# returns dictonary object of json
def ParseJson(json_path):
    with open(json_path) as json_file:
        return json.load(json_file)

# Get list of inputs files be they stls or skeleton data jsons
def GetInputFiles(input_dir):  
    input_directory_files = []
    for file in sorted(os.listdir(input_dir)):
        if file.endswith('.stl'):
            input_directory_files.append(os.path.join(input_dir,file))
    return input_directory_files  

def write_launch_file(file_name, case_name, input_path, output_path, params):
    with open(file_name, 'w') as file:
        file.write('[Main]\n')
        file.write(f'Input = {input_path}\n')
        file.write(f'OutputName = {output_path}\n')
        for key in params:
            value = params[key]
            file.write(key + ' = ' + str(value).replace('*NAME*',case_name) + '\n')

def RunSkeletonize(launchfile_path, exe_path):
    
    start_time = time.time()
    stdout_str = ""

    with subprocess.Popen([exe_path, launchfile_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True) as p:
        try:
            stdout_data, _ = p.communicate(timeout=SKETLTON_TIMEOUT)
            stdout_str += stdout_data
            print(stdout_data, end='')  # This should preserve newlines as in the terminal
            returncode = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            timeout_msg = f"The process took too long (more than {SKETLTON_TIMEOUT} seconds) and was terminated."
            stdout_str += timeout_msg + "\n"
            print(timeout_msg)
            returncode = -1  # or whatever non-zero code you want to use to indicate timeout

        total_time = time.time() - start_time
        success = (returncode == 0)
        return success, total_time, stdout_str
    
def euclidean_distance(p1, p2):
    """Compute the Euclidean distance between two 3D points."""
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)**0.5

def polyline_length(polyline):
    """Compute the length of a polyline."""
    return sum(euclidean_distance(polyline[i], polyline[i+1]) for i in range(len(polyline) - 1))


def ComputeRunMetrics(skeletonJsonData):
    polylines = skeletonJsonData[polylines_key]

    sk_points = []
    raw_sk_points = skeletonJsonData[sk_points_key]
    for i in range(int(len(raw_sk_points)/3)):
        sk_points.append([raw_sk_points[i * 3 + 0],raw_sk_points[i * 3 + 1],raw_sk_points[i * 3 + 2]])  

    bifurcations = {}
    termina_cnt = 0 
    
    # List to store polylines that have both ends as bifurcations
    polylines_between_bifurcations = []
    skeleton_length = 0

    # Loop through each polyline to check its ends
    for current_polyline in polylines:
        start_point = current_polyline[0]
        end_point = current_polyline[-1]

        start_is_bifurcation = False
        end_is_bifurcation = False

        # Check the current polyline's ends against the ends of all other polylines
        for other_polyline in polylines:
            if current_polyline == other_polyline:
                continue

            other_ends = [other_polyline[0], other_polyline[-1]]
            if start_point in other_ends:
                start_is_bifurcation = True
            if end_point in other_ends:
                end_is_bifurcation = True

        if start_is_bifurcation:
            bifurcations[start_point] = 0

        if end_is_bifurcation:
            bifurcations[end_point] = 0

        if start_is_bifurcation and end_is_bifurcation:
            polylines_between_bifurcations.append(current_polyline)

        # if only one condition is true
        if start_is_bifurcation ^ end_is_bifurcation:
            termina_cnt += 1

    sum_degree = 0
    avg_degree = 0
    # Loop over each bifurcation and find its degree
    for bi in bifurcations:
        for polyline in polylines:
            if bi in polyline:
                sum_degree += 1
    avg_degree = sum_degree / len(bifurcations)

    # Loop through each polyline to compute its length
    for polyline_ids in polylines_between_bifurcations:
        polyline = []
        for id in polyline_ids:
            polyline.append(sk_points[id])
        skeleton_length += polyline_length(polyline)

    out_metrics = TRIAL_METRICS.copy()
    out_metrics["bifurcations"] = len(bifurcations)
    out_metrics["termina"] = termina_cnt
    out_metrics["avg_degree"] = avg_degree
    out_metrics["skeleton_length"] = skeleton_length

    return out_metrics

# Main execution logic
def main(args):
    experiment_id = nni.get_experiment_id()
    trial_id = nni.get_trial_id()
    experiment_dirs = setup_directories(experiment_id, trial_id)
    copy_search_space_json(experiment_dirs['experiment_main'], SEARCH_SPACE_JSON)
    report_paths = create_reports(experiment_dirs)
    input_stl_files = GetInputFiles(INPUT_STL_DIR)
    trial_results = run_trial(input_stl_files, experiment_dirs, report_paths, args)
    analize_trial(trial_results, report_paths['experiment'], trial_id, args)

def setup_directories(experiment_id, trial_id):
    # Setup and return a dictionary of necessary directories...

     # working dirs
    experiment_main_dir = os.path.join(OUTPUT_DIR,EXPERIMENT_NAME)
    trial_main_dir = os.path.join(experiment_main_dir,trial_id)
    trial_input_dir = os.path.join(trial_main_dir,"input")
    trial_output_dir = os.path.join(trial_main_dir,"output")
    trial_vtk_dir = os.path.join(trial_main_dir,"vtks")

    # create directories
    Mkdir(experiment_main_dir)
    Mkdir(trial_main_dir)
    Mkdir(trial_input_dir)
    Mkdir(trial_output_dir)
    Mkdir(trial_vtk_dir)

    return {
        'experiment_main': experiment_main_dir,
        'trial_main': trial_main_dir,
        'trial_input': trial_input_dir,
        'trial_output': trial_output_dir,
        'trial_vtk': trial_vtk_dir
    }

def copy_search_space_json(dest_dir, search_space_path):
    # Copy search space JSON to the destination directory if it does not exist...
    copy_ss_path = os.path.join(dest_dir,"search_space.json")
    if not os.path.isfile(copy_ss_path):
        shutil.copy(search_space_path, copy_ss_path)
    pass

def create_reports(dirs):
    # Create main and trial report file if it does not exist...
    main_report_path = os.path.join(dirs['experiment_main'],"Main_Report.csv")
    if not os.path.isfile(main_report_path):
        with open(main_report_path, "a") as txt_file:
                 txt_file.write('Trial_Id, QST, MST, MinEL, Cases_Ran, default, avg_bifurcations, avg_termina, avg_degree, avg_sk_len\n')

    # create trial report
    trail_report_path = os.path.join(dirs['trial_main'],"Trial_Report.csv")
    with open(trail_report_path, "w") as txt_file:
            txt_file.write('Case, passed, bifurcations, terminal_cnt, avg_degree, skeleton_length, Total_Time\n')

    return {
        'experiment': main_report_path,
        'trial': trail_report_path,
    }

def write_trial_data(txt_file_path, case_name, data):
     # write case data to trial report        
        with open(txt_file_path, "a") as txt_file:
            txt_file.write(case_name + "," + 
                           str(data["passed"]) + "," + 
                           str(data["bifurcations"]) + "," + 
                           str(data["termina"]) + "," + 
                           str(data["avg_degree"]) + "," + 
                           str(data["skeleton_length"]) + "," + 
                           str(data["total_time"]) + '\n')
            
def write_experiment_data(txt_file_path, trial_id, passed_cases, data):
     # write case data to trial report        
        with open(txt_file_path, "a") as txt_file:
             txt_file.write(str(trial_id) + "," + 
                            str(data["QualitySpeedTradeoff"]) + "," + 
                            str(data["MedialSpeedTradeoff"]) + "," + 
                            str(data["MinEdgeLength"]) + "," +
                            str(passed_cases) + "," +
                            str(data['default']) + "," + 
                            str(data['avg_bifurcations']) + "," + 
                            str(data['avg_termina']) + "," + 
                            str(data['avg_degree']) + "," + 
                            str(data['avg_sk_len']) + "\n")

        
def run_trial(input_stl_files, dirs, report_paths, params):
    # Run the trial for each STL file...

    trial_params = DEFAULT_PARAMETERS
    trial_params["QualitySpeedTradeoff"] = params["QualitySpeedTradeoff"]
    trial_params["MedialSpeedTradeoff"] = params["MedialSpeedTradeoff"]
    trial_params["MinEdgeLength"] = params["MinEdgeLength"]

    trial_data = {}
    current_case_index = 0
    for input_file in input_stl_files:
        
        print()
        print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        print("-----------  " + str(current_case_index) +"/"+ str(len(input_stl_files)) + "  --------------")
        print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        print()

        case_name = os.path.basename(input_file).split(".stl")[0]

        skeleton_input_file = os.path.join(dirs["trial_input"],case_name + '.txt')
        skeleton_output_dir = os.path.join(dirs["trial_output"],case_name)
        skeleton_output_path = os.path.join(skeleton_output_dir,case_name)

        # make output dir to avoid error when writing clean stl 
        Mkdir(skeleton_output_dir)

        # make skeleton launch file
        write_launch_file(skeleton_input_file, case_name, input_file, skeleton_output_path, trial_params)
        run_pass, run_time, run_sdt_out = RunSkeletonize(skeleton_input_file, SKELETONIZE_EXE)
        print(run_sdt_out)

        
        skeletonData_file = findFile(skeleton_output_dir, case_name+'_SkeletonData.json')
        skeletonData = {}
        #TRIAL_METRICS = { "passed":0,"bifurcations": 0,"termina": 0,"avg_degree": 0,"skeleton_length": 0,"total_time": 0 }
        case_metrics = TRIAL_METRICS.copy()

        if run_pass and skeletonData_file != "NULL":
            skeletonData = ParseJson(skeletonData_file)
            case_metrics = ComputeRunMetrics(skeletonData)
            case_metrics["passed"] = 1
            case_metrics["total_time"] = run_time
            SKJson2VTk.WriteVesselAndCenterlineVtk(skeletonData_file, case_name, dirs["trial_vtk"])

        # if run failed write std output
        else:
            run_error_log_file = os.path.join(skeleton_output_dir,case_name + "_stdout.txt")
            with open(run_error_log_file, 'w') as f:
                f.write(run_sdt_out)

        write_trial_data(report_paths["trial"], case_name, case_metrics)
        trial_data[case_name] = case_metrics
        current_case_index += 1
    return trial_data

def analize_trial(trial_data, experiment_Report_path, trial_id, args):
    # Analize the trial results and write them to the trial report...
    sum_bifurcations = 0
    avg_bifurcations = 0
    sum_termina = 0
    avg_termina = 0
    sum_degree = 0
    avg_degree = 0
    sum_sk_len = 0
    avg_sk_len = 0
    passed_cnt = 0

    default_score = 0
    for case in trial_data:
        data = trial_data[case]
        # run passed
        if data["passed"]:
            sum_bifurcations += data["bifurcations"]
            sum_termina += data["termina"]
            sum_degree += data["avg_degree"]
            sum_sk_len += data["skeleton_length"]
            passed_cnt += 1

    if passed_cnt != 0:
        avg_bifurcations = sum_bifurcations / passed_cnt
        avg_termina = sum_termina / passed_cnt
        avg_degree = sum_degree / passed_cnt
        avg_sk_len += sum_sk_len / passed_cnt

    if passed_cnt:
        default_score = avg_bifurcations
    else:
        default_score = 1e+10
                 
    # ------------------------------- Report -------------------------------
    # ----------------------------------------------------------------------
    scores = {'default': default_score, 'avg_bifurcations': avg_bifurcations, 'avg_termina': avg_termina, 'avg_degree': avg_degree, 'avg_sk_len': avg_sk_len}
    report_data = scores.copy()
    report_data["QualitySpeedTradeoff"] = args["QualitySpeedTradeoff"]
    report_data["MedialSpeedTradeoff"] = args["MedialSpeedTradeoff"]
    report_data["MinEdgeLength"] = args["MinEdgeLength"]
    nni.report_final_result(scores)
    write_experiment_data(experiment_Report_path, trial_id, passed_cnt, report_data)
    pass

if __name__ == '__main__':
    #params = {'QualitySpeedTradeoff': 0.5, 'MedialSpeedTradeoff': 1.5, 'MinEdgeLength': 0.8}
    params = nni.get_next_parameter()
    
    main(params)