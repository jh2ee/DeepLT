from Bio.PDB import PDBParser
import os
import subprocess


def pass_creation(jobid, path_ligand, nanobody_pass):
    # nanobody .pass file 생성
    # passive residue 입력으로 받음 ex) 90 91 92
    # 미입력시 모든 residue를 passive residue 처리
    if nanobody_pass == '':
        # 모든 residue를 passive residue로 처리
        parser = PDBParser()
        structure = parser.get_structure('Antibody', path_ligand)

        # 항체 체인 ID 설정 (예: H)
        antibody_chain_id = 'H'

        # 체인 H의 모든 잔기 번호 추출
        chain = structure[0][antibody_chain_id]
        residues = [residue.get_id()[1] for residue in chain.get_residues()]

        # .pass 파일 생성
        with open(f'{jobid}.pass', 'w') as pass_file:
            pass_file.write('\n')
            pass_file.write(' '.join(map(str, residues)))
            pass_file.write('\n')
        print('.pass created')

    else:
        # 입력된 residue passive로 처리
        # .pass 파일로 저장
        with open(f'{jobid}.pass', 'w') as file:
            file.write('\n')            # 첫 줄을 비워둠
            file.write(nanobody_pass)   # 둘째 줄: passive residue
            file.write('\n')            # 세 번째 줄을 비워둠
        print('.pass created')


def act_creation(jobid, path_receptor, antigen_act):
    # antigen .act-pass file 생성
    # active residue 입력 ex) 122 123 124 ...
    # 미입력시 tbl 파일 생성하지 않고 도킹?
    if antigen_act == '':
        # 모든 residue를 active residue로 지정
        parser = PDBParser()
        structure = parser.get_structure('Antigen', path_receptor)

        # 항체 체인 ID 설정
        antibody_chain_id = 'A'

        # 체인 H의 모든 잔기 번호 추출
        chain = structure[0][antibody_chain_id]
        residues = [residue.get_id()[1] for residue in chain.get_residues()]

        with open(f'{jobid}.act-pass', 'w') as file:
            file.write('\n')                            # 첫 줄 비우기
            file.write(' '.join(map(str, residues)))    # 모든 residue passive로 처리
        print('.act-pass created')

    else:
        # antigen_act 변환
        antigen_act_str = antigen_act.replace(" ", ",")
        command = f"haddock3-restraints passive_from_active {path_receptor} {antigen_act_str}"

        # subprocess를 사용하여 명령어 실행 및 출력 캡처
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            output = result.stdout
            with open(f'{jobid}.act-pass', 'w') as file:
                file.write(antigen_act) # 첫 줄: active residue
                file.write('\n')
                file.write(output)      # 둘째 줄: passive residue
            print('.act-pass created')
        else:
            print(f"Error: {result.stderr}")


def tbl_creation(jobid):
    command = f"haddock3-restraints active_passive_to_ambig {jobid}.act-pass {jobid}.pass --segid-one A --segid-two H > {jobid}.tbl"
    subprocess.call(command, shell=True)
    # haddock3-restraints active_passive_to_ambig [act-pass_file] [pass_file] --segid-one [antigen_chain] --segid-two [antibody_chain] > ambig.tbl
    print('.tbl created')