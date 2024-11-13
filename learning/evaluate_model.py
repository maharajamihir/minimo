import argparse
import io
import os
import torch
import json
import policy
import worker
import peano
import bootstrap
from tqdm import tqdm



#############################################################################################################################################################
#               Script to evaluate the model on the final goals. Make sure it is in the learning/ folder                                                    #                                                  
#               Usage: python learning/evaluate_model.py --run_dir outputs/2024-11-12/23-22-47/ --final_goal_path "../gc-minimo/goals/nat-add-hard.json"    # 
#############################################################################################################################################################

def load_final_goals(path):
    goals_dict = json.load(open(path))
    final_goals = []
    solutions = []
    for goal in goals_dict["goals"]:
        final_goals.append(goal["theorem"])
        solutions.append(goal["solution"])

    return final_goals, solutions

def prove_conjectures(agent_dump, conjectures, theory, premises):
    tasks = []
    print('Submitting tasks...')
    for conjecture in tqdm(conjectures, miniters=1):
        tasks.append(bootstrap.submit_task(
            agent_dump,
            worker.BackgroundTheory(theory, premises),
            conjecture))

    student_results = []

    print('Collecting %d results from workers.', len(tasks))

    for task in tqdm(tasks, miniters=1):
        student_result = bootstrap.get_task_result(task)

        if student_result.error:
            print('Error in prover process!')
            print(student_result.error)
            continue

        student_results.append(student_result)
    return student_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", help="Path to the run directory")
    parser.add_argument("--theory_path", help="Path to the theory.p file")
    parser.add_argument("--final_goal_path", help="Path to the final goal file")
    args = parser.parse_args()

    # Create a dictionary to store the parsed arguments
    arguments = {
        "run_dir": args.run_dir,
        "final_goal_path": args.final_goal_path
    }
    print("evaluating model" , args.run_dir, "on", args.final_goal_path)

    theory_dict = {'name': 'nat-add', 'premises': ['eq_refl', 'eq_symm', 'rewrite', '+_z', '+_s', 'nat_ind']}
    with open(os.path.join(os.path.dirname(__file__), 'theories', theory_dict["name"] + '.p')) as f:
        theory = f.read()

    premises = theory_dict["premises"]
    d = peano.PyDerivation()
    d.incorporate(theory)

    # Verify that the model.pt file exists in the run_dir
    model_path = os.path.join(args.run_dir, "model.pt")
    if os.path.exists(model_path):
        # Import the model
        # Load the model
        model = torch.load(model_path)
    else:
        assert False, f"model.pt file does not exist in the run_dir: {args.run_dir}"
    # load final_goal from final_goal_path 
    final_goal_path = args.final_goal_path

    if os.path.exists(final_goal_path):
        if final_goal_path.endswith('.json'):
            with open(final_goal_path, 'r') as file:
                final_goals_formatted, solutions = load_final_goals(final_goal_path)
        else:
            assert False, f"final_goal_path is not a JSON file: {final_goal_path}"
    else:
        assert False, f"final_goal_path does not exist: {final_goal_path}"

    # dump the model 
    buff = io.BytesIO()
    torch.save(model, buff)
    agent_dump = buff.getvalue()
    # Evaluate the model
    final_goals = ["Conj:(hard) " + g for g in final_goals_formatted]
    student_results_final = prove_conjectures(agent_dump, final_goals_formatted, theory, premises)
    results = {}
    proven = 0
    for s in student_results_final:
        results[s.problem] = s.success
        if s.success:
            proven += 1

    print('Proven:', proven, '/', len(final_goals))
    print('Results:\n', results)



if __name__ == "__main__":
    main()