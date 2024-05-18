import os
import subprocess
import tempfile
import shutil
import stat
import errno  # Import errno module
from analyzer import analyze_files
from graph import create_dependency_graph, save_graph
from flask import jsonify

def get_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def clone_github_repo(github_url):
    temp_dir = tempfile.mkdtemp()
    subprocess.run(['git', 'clone', github_url, temp_dir], check=True)
    return temp_dir

def handle_remove_readonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        func(path)
    else:
        raise

def cleanup_temp_dir(directory):
    try:
        shutil.rmtree(directory, onerror=handle_remove_readonly)
    except Exception as e:
        print(f"Error cleaning up temp directory {directory}: {e}")

def generate_summary_github(all_imports, all_functions, github_url, temp_dir):
    summary = {
        'imports': {},
        'functions': {}
    }

    for filepath, imports in all_imports.items():
        # Convert the full path to a relative path
        relative_path = os.path.relpath(filepath, temp_dir)
        # Construct GitHub URL for the file
        github_filepath = os.path.join(github_url.rstrip('/'), 'blob/main', relative_path.replace('\\', '/'))
        summary['imports'][github_filepath] = list(imports.keys())

    for filepath, functions in all_functions.items():
        # Convert the full path to a relative path
        relative_path = os.path.relpath(filepath, temp_dir)
        # Construct GitHub URL for the file
        github_filepath = os.path.join(github_url.rstrip('/'), 'blob/main', relative_path.replace('\\', '/'))
        summary['functions'][github_filepath] = list(functions.keys())

    return summary

def generate_summary(all_imports, all_functions, upload_dir):
    summary = {
        'imports': {},
        'functions': {}
    }

    for filepath, imports in all_imports.items():
        relative_path = os.path.relpath(filepath, upload_dir)
        summary['imports'][relative_path] = list(imports.keys())

    for filepath, functions in all_functions.items():
        relative_path = os.path.relpath(filepath, upload_dir)
        summary['functions'][relative_path] = list(functions.keys())

    return summary


def process_project(project_path):
    python_files = get_python_files(project_path)
    all_imports, all_functions = analyze_files(python_files)
    G = create_dependency_graph(all_imports, all_functions)
    output_path = os.path.join(tempfile.gettempdir(), 'dependency_graph.png')
    save_graph(G, output_path)
    summary = generate_summary_github(all_functions)
    return jsonify({'summary': summary, 'graph': output_path})
