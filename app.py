from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import requests
from celery import Celery, uuid
import os
from job import nanobodybuilder, diffdock, haddock, GNN_DOVE, Diffpack, isFullAtom, download_pdb_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, methods=["POST"], allow_headers=["Content-Type", "Authorization"])
app.secret_key = os.getenv('APP_SECRET_KEY')

# job list for download feature
job_list = []

API_URL = os.getenv('API_URL')
API_TOKEN = os.getenv('API_TOKEN')

# Celery 설정
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

def call_gpt_api(message):
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {"message": message}  # JSON 형식으로 body에 포함
    
    try:
        # POST 요청으로 수정
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # 에러가 발생하면 예외 발생
        print("GPT API Response:", response.json())  # 응답 출력

        # pdb id 추출, docking 전달
        if response.json().get('firstPdbId'):
            first_id, second_id = response.json().get('firstPdbId')[0], response.json().get('secondPdbId')[0]
            print(first_id, second_id)
            call_docking_module(first_id, second_id)

        return response.json().get('content', 'No response')
    
    except requests.RequestException as e:
        print(f"Error communicating with GPT model API: {e}")
        return "유효하지 않은 요청입니다."

def call_docking_module(pdb_id1, pdb_id2):
    job_id = str(uuid())
    print(job_id)
    os.makedirs(f'../vol/{job_id}')

    download_pdb_file(pdb_id1, 'ligand', job_id)
    download_pdb_file(pdb_id2, 'receptor', job_id)
    
    task = deeplt_task.apply_async(
        args=[job_id, None, 1, 'haddock', None, None, 40, 0], 
        task_id=job_id
    )
    job_list.append({'job_id': job_id, 'task': task, 'status': 'Processing'})
    flash(f"Job {job_id} has been submitted!")

    return redirect(url_for('download'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat')
def chat():
    initial_query = request.args.get('initial_query', '')
    gpt_response = request.args.get('gpt_response', '')
    return render_template('chat.html', initial_query=initial_query, gpt_response=gpt_response)

@app.route('/manual')
def manual():
    return render_template('manual.html')

@app.route('/download')
def download():
    return render_template('download.html')

@app.route('/process_query', methods=['POST'])
def process_query():
    print("process_query endpoint called")  # 디버그 메시지 추가
    data = request.get_json()
    user_message = data.get('message') if data else None
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    print("User Message:", user_message)  # 수신된 메시지 확인
    
    gpt_response = call_gpt_api(user_message)
    return jsonify({'response': gpt_response})

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data.get('message')
    if not user_message:
        return jsonify({'response': "Error: No message provided"})

    gpt_response = call_gpt_api(user_message)
    return jsonify({'user_message': user_message, 'response': gpt_response})

# Celery 작업을 위한 task 정의
@celery.task()
def deeplt_task(j_id, content, n_structure, docking_tool, antigen_act, nanobody_pass, decoy, is_manual):
    print('start program_running')
    if is_manual:
        nanobodybuilder(j_id, content, n_structure)

    if docking_tool == 'haddock':
        haddock(j_id, n_structure, antigen_act, nanobody_pass, decoy)
        isFullAtom(j_id)
    elif docking_tool == 'diffdock':
        diffdock(j_id)
        Diffpack(j_id)
        GNN_DOVE(j_id)
    else:
        print(f"Unsupported docking tool: {docking_tool}")

        # 작업 완료 시 상태 업데이트
    for job in job_list:
        if job['job_id'] == j_id:
            job['status'] = 'Completed'
            break

# POST 요청 처리
@app.route('/manual', methods=['POST'])
def run_docking():
    sequence = request.form.get('content').upper()
    n_structure = int(request.form.get('n_structure'))
    docking_tool = request.form.get('docking')
    antigen_act = nanobody_pass = decoy = None

    if docking_tool == 'haddock':
        antigen_act = request.form.get('antigen_act')
        nanobody_pass = request.form.get('nanobody_pass')
        decoy = request.form.get('decoy')

    job_id = str(uuid())
    pdb_file = request.files['pdb_file']
    os.makedirs(f'../vol/{job_id}')
    pdb_file.save(f'../vol/{job_id}/{job_id}_receptor.pdb')

    task = deeplt_task.apply_async(
        args=[job_id, sequence, n_structure, docking_tool, antigen_act, nanobody_pass, decoy, 1], 
        task_id=job_id
    )
    job_list.append({'job_id': job_id, 'task': task, 'status': 'Processing'})
    flash(f"Job {job_id} has been submitted!")
    return redirect(url_for('download'))

@app.route('/job_statuses', methods=['GET'])
def job_statuses():
    # job_list에 저장된 작업 정보를 JSON 형식으로 반환
    job_status_data = [
        {
            'job_id': job['job_id'],
            'status': job['task'].status if job['task'] else 'Unknown'
        } for job in job_list
    ]
    return jsonify(job_status_data)

@app.route('/download/<jobid>')
def download_result(jobid):
    folder_path = f"../vol/{jobid}"
    zip_file = f"{jobid}_result.zip"

    # Check if the folder exists
    if not os.path.exists(folder_path):
        abort(404, description=f"Folder '{folder_path}' not found")

    # Create a zip file of the folder
    try:
        shutil.make_archive(zip_file.split('.')[0], 'zip', folder_path)
    except Exception as e:
        return f"Failed to create ZIP archive: {str(e)}"

    # Send the zip file to the client for download
    try:
        return send_file(zip_file, mimetype='zip', download_name='result.zip', as_attachment=True)
    except Exception as e:
        return f"Failed to send file: {str(e)}"

@app.route('/process_status/<job_id>', methods=['GET'])
def process_status(job_id):
    job = next((job for job in job_list if job['job_id'] == job_id), None)
    if job:
        return jsonify({'status': job['status']})
    else:
        return jsonify({'error': 'Job not found'}), 404

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)