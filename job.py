import os
import shutil
import toml
import pandas as pd
import subprocess
import prody
import csv
import requests
from ImmuneBuilder import NanoBodyBuilder2
from act_pass_ambig import pass_creation, act_creation, tbl_creation
from pyrosetta import *
 

def nanobodybuilder(jobid, content, n_structure=1):    
    print('Structure Prediction Started')
    input_dir = f'../vol/{jobid}'

    if n_structure == 1:
        file_name = jobid + f'_ligand.pdb'
        subprocess.call(['NanoBodyBuilder2', '-H', content, '-o', file_name, '-v'])
        os.system(f'mv {file_name} {input_dir}')
    else:
        for i in range(0, n_structure):
            file_name = jobid + f'_ligand_{i}.pdb'
            subprocess.call(['NanoBodyBuilder2', '-H', content, '-o', file_name, '-v'])
            os.system(f'mv {file_name} {input_dir}')
            
    print('Moved to vol, job finished')


def diffdock(jobid):
    print('Docking started')

    path_receptor = f"../vol/{jobid}/{jobid}_receptor.pdb"
    path_ligand = f"../vol/{jobid}/{jobid}_ligand.pdb"

    # Ligand Processing
    ligand_pdb = f"{jobid}_l_b.pdb"
    try:
        shutil.copy(path_ligand, ligand_pdb)
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred:", e)

    # Receptor Processing
    receptor_pdb = f"{jobid}_r_b.pdb"  
    try:
        shutil.copy(path_receptor, receptor_pdb)
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred:", e)

    # Move to DiffDock Directory
    print("\nStart Docking process.")
    bash_script = f"mv {ligand_pdb} ../Docking/DiffDock-PP/datasets/single_pair_dataset/structures\n"
    bash_script += f"mv {receptor_pdb} ../Docking/DiffDock-PP/datasets/single_pair_dataset/structures"

    print('processing for csv')
    os.system(bash_script)
    path = '../Docking/DiffDock-PP/datasets/single_pair_dataset/structures'
    pdbs_unique = {i.split('_')[0] for i in os.listdir(path) if i.endswith('.pdb')}
    number_docks = len(pdbs_unique)

    # df = pd.DataFrame({'path':[path+'/'+pdb for pdb in pdbs_unique],
    #                    'split':number_docks*['test']})
    df = pd.DataFrame({'path':[pdb for pdb in pdbs_unique],
                       'split':number_docks*['test']})

    print('creating csv')
    # df.to_csv(path+'/dock.csv', index=False)
    df.to_csv('../Docking/DiffDock-PP/datasets/single_pair_dataset/splits_test.csv', index=False)

    print('start docking')
    # os.system("cd ../Docking/DiffDock-PP && . activate base && sh src/db5_inference.sh")
    os.system("cd ../Docking/DiffDock-PP && bash -c '. activate base && sh src/db5_inference.sh'")
    
    # Move to Docker Volume
    os.makedirs(f'../vol/{jobid}/docking')
    os.system(f"mv ../Docking/DiffDock-PP/visualization/epoch-0/{jobid}/* ../vol/{jobid}/docking")
    
    # Remove Dumped Data
    print("\n\n\nRemoving dumped data...")
    os.system(f"rm ../Docking/DiffDock-PP/datasets/single_pair_dataset/structures/{jobid}_r_b.pdb")
    os.system(f"rm ../Docking/DiffDock-PP/datasets/single_pair_dataset/structures/{jobid}_l_b.pdb")
    os.system(f"rm ../Docking/DiffDock-PP/datasets/single_pair_dataset/splits_test.csv")
    os.system(f"rm ../Docking/DiffDock-PP/datasets/single_pair_dataset/splits_test_cache_v2_b.pkl")
    os.system(f"rm ../Docking/DiffDock-PP/datasets/single_pair_dataset/splits_test_esm_b.pkl")
    
    print("Docking process finished!")


# Haddock
def haddock(jobid, n_structure, antigen_act, nanobody_pass, decoy):
    print('Docking started')

    if n_structure == 1:
        path_ligand = f"../vol/{jobid}/{jobid}_ligand.pdb"      # nanobody
    else:
        ensemble_list = []
        path_ligand = f"../vol/{jobid}/{jobid}_ligand.pdb"      # nanobody

        for i in range(0, n_structure):
            ensemble_list.append(f"../vol/{jobid}/{jobid}_ligand_{i}.pdb")
        
        # ensemble_str 생성
        ensemble_str = ' '.join(ensemble_list)
        path_ligand = f"../vol/{jobid}/{jobid}_ligand.pdb"
        
        command = f"pdb_mkensemble {ensemble_str} > {path_ligand}"
        subprocess.call(command, shell=True)

    path_receptor = f"../vol/{jobid}/{jobid}_receptor.pdb"  # antigen
    config_path = f"../Docking/haddock3/sample.cfg"         # 'config_path'로 변경
    new_config_path = f"./{jobid}_config.cfg"  # new config path

    if antigen_act:
        # ambig 파일 생성
        # act-pass-ambig.py의 function들 호출
        pass_creation(jobid, path_ligand, nanobody_pass)
        act_creation(jobid, path_receptor, antigen_act)
        tbl_creation(jobid)

    try:
        shutil.copyfile(config_path, new_config_path)
        # Config 파일 읽기
        with open(new_config_path, 'r') as f:
            config_data = f.read()

        # TOML 형식으로 파싱
        config = toml.loads(config_data)

        # output 경로
        run_dir = './docking'
        config['run_dir'] = run_dir

        # molecules 리스트에 path_receptor와 path_ligand 추가
        config['molecules'] = [
            path_receptor,
            path_ligand
        ]
        
        # ambig_fname 값을 업데이트할 섹션 목록
        sections_to_update = ['rigidbody', 'mdref']

        if antigen_act:
            # 각 섹션의 ambig_fname 값을 업데이트
            for section in sections_to_update:
                if section in config and 'ambig_fname' in config[section]:
                    config[section]['ambig_fname'] = f'{jobid}.tbl'
        
        if decoy != "":
            config['rigidbody']['sampling'] = int(decoy)

       # 수정된 Config 파일 저장
        with open(new_config_path, 'w') as f:
            toml.dump(config, f)

        # HADDOCK3 실행
        subprocess.call(['haddock3', new_config_path])

        # mv haddock output, rm cache
        os.system(f"mv ./docking ../vol/{jobid}")
        os.system(f"rm ./{jobid}_config.cfg")
        if antigen_act:
            os.system(f"rm ./{jobid}.act-pass")
            os.system(f"rm ./{jobid}.pass")
            os.system(f"rm ./{jobid}.tbl")        
        print('Docking finished successfully')
    
    except Exception as e:
        print(f"An error occurred: {e}")


# DiffPack
def Diffpack(jobid):
    folder_path = f'../vol/{jobid}/docking'
    
    # 파일 경로 포함하여 리스트 생성
    all_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path)]
    
    # 리스트를 공백을 기준으로 결합된 문자열로 변환
    all_files_str = ' '.join(all_files)


    os.system(f'cd ../DiffPack \n python script/inference.py -c config/inference_confidence.yaml \
                           --seed 2023 \
                           --output_dir ../vol/{jobid}/diffpack \
                           --pdb_files {all_files_str}')


# reranking processes
def fix_pdb(receptor_path, ligand_path, outfile_name):
    receptor = prody.parsePDB(receptor_path)
    ligand = prody.parsePDB(ligand_path)
    combine = receptor + ligand

    temp_file = "temp_file.pdb"
    prody.writePDB(temp_file, combine)

    with open(temp_file, 'r') as f:
        lines = f.readlines()

    with open(outfile_name, 'w') as f:
        current_chain = ""
        for line in lines:
            if line.startswith("ATOM"):
                chain_id = line[21]
                if chain_id != current_chain:
                    if current_chain != "":
                        f.write("TER\n")
                    current_chain = chain_id
            f.write(line)

    os.remove(temp_file)

def preprocessing(jobid):
    print('preprocessing data..')
    receptor_path = f"../vol/{jobid}/diffpack/{jobid}-receptor.pdb"
    
    input_dir = f"../Reranking/Input/{jobid}"
    if os.path.exists(input_dir):
        shutil.rmtree(input_dir)
    os.makedirs(input_dir)
    
    for i in range(1, 41):
        ligand_path = f"../vol/{jobid}/diffpack/{jobid}-ligand-{i}.pdb"
        outfile_name = f"../Reranking/Input/{jobid}/{jobid}-complex-{i}.pdb"
        fix_pdb(receptor_path, ligand_path, outfile_name)
        
def reranking(jobid):
    # 경로 임시 변경
    original_cwd = os.getcwd()
    model_cwd = os.path.abspath(os.path.join('..', 'Reranking', 'GNN_DOVE'))
    try:
        os.chdir(model_cwd)
        # Call the model script
        os.system(f"python main.py --mode=1 -F=../Input/{jobid} --gpu=0 --fold=-1")
    finally:
        os.chdir(original_cwd)

def move_to_Result(jobid):
    os.makedirs(f'../vol/{jobid}/reranked')
    os.system(f"mv ../Reranking/GNN_DOVE/Predict_Result/Multi_Target/Fold_-1_Result/{jobid}/* ../vol/{jobid}/reranked")
    os.system(f'rmdir ../Reranking/GNN_DOVE/Predict_Result/Multi_Target/Fold_-1_Result/{jobid}/')

def GNN_DOVE(jobid):
    print("Reranking started")
    prody.confProDy(verbosity='critical')
    preprocessing(jobid)
    print("Results are successfully saved in the /Reranking/Input directory.\n\n\n")
    
    
    print("Starting reranking.")
    reranking(jobid)
    
    print("\n\n\nMove the results to the /vol/{jobid}/reranked diretory.")
    move_to_Result(jobid)
    print("Completed Successfully.")


# IS FULL ATOM ?
# PyRosetta 초기화
def initialize_rosetta():
    init()

# PDB 파일이 full atom 구조인지 확인
def is_full_atom(pdb_file):
    try:
        pose = pose_from_file(pdb_file)
        for atom in pose.residues:
            if atom.is_fullatom():
                continue
            else:
                return False
        return True
    except Exception as e:
        print(f"Error processing {pdb_file}: {e}")
        return False

# 지정된 경로의 모든 PDB 파일에 대해 full atom 여부 확인
def check_pdb_files(jobid):
    directory = f"../vol/{jobid}/docking/2_mdref"
    pdb_files = [f for f in os.listdir(directory) if f.endswith('.pdb')]
    
    results = []
    for pdb in pdb_files:
        pdb_path = os.path.join(directory, pdb)
        is_full_atom_status = is_full_atom(pdb_path)
        results.append((pdb, is_full_atom_status))
    
    return results

# 결과를 CSV 파일로 저장
def save_results_to_csv(jobid, results):
    csv_file = f"../vol/{jobid}/docking/is_full_atom.csv"
    with open(csv_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["PDB Name", "Is Full Atom"])
        writer.writerows(results)
    print(f"Results saved to {csv_file}")

# 전체 프로세스를 수행하는 함수
def isFullAtom(jobid):
    initialize_rosetta()
    results = check_pdb_files(jobid)
    save_results_to_csv(jobid, results)



# pdb download 함수
def download_pdb_file(pdb_id, type, jobid):
    # PDB 파일 경로를 설정
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    path = f'../vol/{jobid}/{jobid}_{type}.pdb'

    # PDB 파일 다운로드
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, 'w') as file:
                file.write(response.text)
            if type == 'ligand':
                modify_chain(jobid)
            print(f"Downloaded {path}")
        else:
            raise Exception(f"Failed to download PDB file: {pdb_id}")

    except requests.RequestException as e:
        return f"Failed to download PDB file for ID {pdb_id}. Error: {e}", 500

def modify_chain(jobid):
    # ligand pdb chain modify
    path = f'../vol/{jobid}/{jobid}_ligand.pdb'

    command = f'pdb_chain -X {path} > {path}'
    subprocess.run(command, shell=True, check=True)