import re
import random
import argparse
from typing import List, Tuple
import pandas as pd

INVERSE_RELATION = {
    "north":"south",
    "south":"north",
    "east":"west",
    "west":"east",
    "northeast":"southwest",
    "southwest":"northeast",
    "southeast":"northwest",
    "northwest":"southeast",
    
    "adjacent to and north":"adjacent to and south",
    "adjacent to and south":"adjacent to and north",
    "adjacent to and east":"adjacent to and west",
    "adjacent to and west":"adjacent to and east",
    "adjacent to and northeast":"adjacent to and southwest",
    "adjacent to and southwest":"adjacent to and northeast",
    "adjacent to and southeast":"adjacent to and northwest",
    "adjacent to and northwest":"adjacent to and southeast",
    
    "inside":"contains",
    "contains":"inside",
    "intersects with":"intersects with",   # relation intersects
    "they intersect":"they intersect",     # 新增:以防出现这种写法
}

relation_pool = ["north of", "south of", "east of", "west of", 
                 "northeast of", "southeast of", "northwest of", "southwest of", 
                 "adjacent to and north of", "adjacent to and south of", "adjacent to and east of", "adjacent to and west of", 
                 "adjacent to and northeast of", "adjacent to and southeast of", "adjacent to and northwest of", "adjacent to and southwest of",
                 "inside of", "contains", "they intersect"]

POS_TO_LETTER = {0:"a.", 1:"b.", 2:"c.", 3:"d."}

ENTITY_MAP = {}
# 8 方向环(用于生成近邻方向题)
CYCLE = ['north','northeast','east','southeast','south','southwest','west','northwest']

def neighbor_relation(pred, steps=1):
    """返回方向 pred 在环上偏移 steps 步的邻居(随机左偏或右偏)。
       拓扑关系(inside/contains/intersects)没有方向邻居,返回 None。"""
    base = pred.replace('adjacent to and ', '')
    if base not in CYCLE:
        return None
    i = CYCLE.index(base)
    offset = random.choice([-steps, steps])
    neighbor = CYCLE[(i + offset) % 8]
    if pred.startswith('adjacent to and '):
        neighbor = 'adjacent to and ' + neighbor
    return neighbor

def generate_neighbor_yesno_question(triple, steps=1):
    subj, pred, obj = triple
    # 关键修复:函数一开始就拦截拓扑关系,yes/no 两个分支都受保护
    if pred.replace('adjacent to and ', '') not in CYCLE:
        return None, None, None

    ask_correct = random.random() < 0.5
    if ask_correct:
        asked = pred                          # 问真实方向本身
        truth = "yes"
        angular_distance = 0
    else:
        asked = neighbor_relation(pred, steps)  # 问邻居方向
        if asked is None:                        # 双保险(理论上前面已拦截)
            return None, None, None
        truth = "no"
        angular_distance = steps * 45            # 加回 angular:45/90/180...
    question = f"Is {subj} {asked} of {obj}?"
    return question, truth, angular_distance      # 返回 3 个值
 #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------   

def parse_nt_file(file_path: str) -> List[Tuple[str, str, str]]:
    """
    Parse an N-Triples file and extract subject, predicate, object triples without URIs
    """
    triples = []
    uri_pattern = re.compile(r'<http://spatex.org/(.*?)>')


    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # skip empty lines and comments
                
            # Match the triple pattern
            match = re.match(r'^<.+?> <.+?> <.+?> \.$', line)
            if not match:
                print(f"Skipping malformed line: {line}")
                continue
                
            # Extract components
            try:
                subj = uri_pattern.search(line).group(1).replace('_', ' ')
                pred = uri_pattern.search(line.split()[1]).group(1).replace('_', ' ')
                obj = uri_pattern.search(line.split()[2]).group(1).replace('_', ' ')
                if obj[-1] == ".":
                    obj = obj[:-1]
                triples.append((subj, pred, obj))
                
                # add to entity map
                if subj in ENTITY_MAP:
                    if pred in ENTITY_MAP[subj]:
                        ENTITY_MAP[subj][pred].append(obj)
                    else:
                        ENTITY_MAP[subj][pred] = [obj]
                else:
                    ENTITY_MAP[subj] = {pred:[obj]}
                    
            except Exception as e:
                print(f"Error parsing line: {line}\nError: {e}")
    
    return triples

def generate_yesno_question(triple: Tuple[str, str, str]) -> str:
    """Generate a yes/no question from a triple"""
    subj, pred, obj = triple
    truth = ""
    question = ""
    # generate yes or no query
    yes = random.randint(0,1)

    if yes == 0:
        # generate yes query
        question = f"Is {subj} {pred} of {obj}?"
        truth = "yes"
    else:
        # generate no query
        inverse_relation = INVERSE_RELATION[pred]
        question = f"Is {subj} {inverse_relation} of {obj}?"
        truth = "no"
    
    # print(f"question: {question}, truth: {truth}")
    return question, truth

def getRandomRelations(truth, n):
    filtered_list = [item for item in relation_pool if item != truth]
    
    # Check if there are enough items left
    if n > len(filtered_list):
        raise ValueError("Not enough unique elements to choose from.")
    
    # Randomly pick n unique elements
    return random.sample(filtered_list, n)

def generate_radio_question(triple: Tuple[str, str, str]) -> str:
    """Generate a multiple choice (radio) question from a triple"""
    subj, pred, obj = triple
    truth = ""
    
    # 20% chance: Correct answer is NOT in a-d ("None of the above" is true)
    is_none_correct = random.random() < 0.2
    
    if is_none_correct:
        # Generate 4 random wrong options (a-d) + "None of the above" (e, correct)
        wrong_options = getRandomRelations(pred, 4)
        options = wrong_options + ["none of the above"]
        truth = "e."  # "None of the above" is correct
    else:
        # Include correct answer + 3 wrong options (a-d) + "None of the above" (e, wrong)
        wrong_options = getRandomRelations(pred, 3)
        options = [pred] + wrong_options
        random.shuffle(options)
        truth = POS_TO_LETTER[options.index(pred)]  # Correct answer is a-d
        options = options + ["none of the above"]
    
    # Build query (options a-e)
    question = (
        f"Question: Select exactly one option (a-e) that best describes the relationship of {subj} in relation to {obj} in terms of geography. "
        f"Options: a. {options[0]} b. {options[1]} c. {options[2]} d. {options[3]} e. {options[4]}"
    )
    
    # print(f"subj: {subj}, pred: {pred}, obj: {obj}")
    # print(f"question: {question}, truth: {truth}")
    return question, truth

def generate_checkbox_question(triple: Tuple[str, str, str], total_options: int = 4) -> str:
    """Generate a checkbox question from multiple triples"""
    subj, pred, obj = triple
    
    # get one random relation tied to the primary entity
    random_relation = random.choice(list(ENTITY_MAP[subj].keys()))
    selection = ENTITY_MAP[subj][random_relation]

    # pick random correct options from the available ones
    total_correct_answers = random.randint(0, min(total_options, len(selection)))
    correct_answers = random.sample(selection, total_correct_answers)
    
    options = correct_answers.copy()
        
    # generate wrong choices from the rest of the relations related to the entity
    total_wrong_answers = total_options - total_correct_answers
    if total_wrong_answers > 0:
        # Collect all entities from other relations
        other_relations = [
            rel for rel in ENTITY_MAP[subj] if rel != random_relation
        ]

        # Flatten all entities from other relations
        wrong_candidates = []
        for rel in other_relations:
            wrong_candidates.extend(ENTITY_MAP[subj][rel])

        # Ensure we have enough to sample
        if len(wrong_candidates) < total_wrong_answers:
            print("Warning: Not enough wrong candidates. Exiting...")
            # todo: generate random
            exit(-1)
        else:
            wrong_answers = random.sample(wrong_candidates, total_wrong_answers)

        # append the wrong options 
        options += wrong_answers
    
    # shuffle all options
    random.shuffle(options)
    
    # map option letters to options
    option_letters = ['a', 'b', 'c', 'd']
    labeled_options = [(option_letters[i], option) for i, option in enumerate(options)]
    labeled_options.append(('e', 'None of the above'))
    
    truth = ""
    if total_correct_answers > 0:
        # generate the truth in format: a. <name>, b. <name>, ...
        correct_letters = [label for label, option in labeled_options if option in correct_answers]
        truth = ",".join(correct_letters)
    else:
        # no true answers = e. None of the above
        truth = "e"
        
    # generate query
    question = ""        
    if "intersects" in random_relation:
        question = f"Question: Select all options that intersect with {subj}? You may choose one or more options. Options: " + \
                " ".join([f"{label}. {option}" for label, option in labeled_options])
    elif "contains" in random_relation:
        question = f"Question: Select all options that are inside of {subj}? You may choose one or more options. Options: " + \
                " ".join([f"{label}. {option}" for label, option in labeled_options])
    else:
        question = f"Question: Select all options that are {random_relation} {subj}? You may choose one or more options. Options: " + \
                " ".join([f"{label}. {option}" for label, option in labeled_options])
        
    # print(f"subj: {subj}, pred: {pred}, obj: {obj}")
    # print(f"question: {question}, truth: {truth}")
    return question, truth

def main():
    parser = argparse.ArgumentParser(description='Generate questions from RDF triples')
    parser.add_argument('-input', required=True, help='Path to the input N-Triples file')
    parser.add_argument('-output', default="questions.csv", help='Path to the output file where to write the questions')
    parser.add_argument('-num', type=int, required=True, help='Total number of questions to generate')
    parser.add_argument('-yesno', type=float, default=0.33, help='Proportion of yes/no questions')
    parser.add_argument('-radio', type=float, default=0.33, help='Proportion of radio questions')
    parser.add_argument('-checkbox', type=float, default=0.34, help='Proportion of checkbox questions')
    parser.add_argument('-steps', type=int, default=1, help='Neighbour distance in 45-degree so steps should is 1')
    parser.add_argument('-neighbor_output', default='queries_yesno_neighbor.csv', help='Output path for neighbour questions')

    
    args = parser.parse_args()
    
    # Validate proportions
    total = args.yesno + args.radio + args.checkbox
    if not (0.99 <= total <= 1.01):  # Allow for floating point imprecision
        print("Error: Question proportions must sum to 1.0")
        return
    
    # Parse the NT file
    triples = parse_nt_file(args.input)
    if not triples:
        print("No valid triples found in the input file")
        return
    
    # Sample the requested number of triples
    if len(triples) < args.num:
        print(f"Warning: Only {len(triples)} triples available, using all")
        sampled_triples = triples
    else:
        sampled_triples = random.sample(triples, args.num)
    
    # Calculate number of each question type
    num_yesno = int(args.num * args.yesno)
    num_radio = int(args.num * args.radio)
    num_checkbox = args.num - num_yesno - num_radio  # Ensure we get exactly N questions
    
    # Generate questions
    questions = []
    
    # Yes/No questions
    # for triple in sampled_triples[:num_yesno]:
    #     query, truth = generate_yesno_question(triple)
    #     questions.append(("yes/no", query, truth))
        
    # Radio questions
    # for triple in sampled_triples[num_yesno:num_yesno+num_radio]:
    #     question, truth = generate_radio_question(triple)
    #     questions.append(("radio", question, truth))
    
    # Checkbox questions
    # for triple in sampled_triples[num_radio:num_radio+num_checkbox]:
    #     question, truth = generate_checkbox_question(triple)
    #     questions.append(("checkbox", question, truth))
    
    # Convert the list to a pandas DataFrame
    #df = pd.DataFrame(questions, columns=["type", "question", "truth"])

    # Write the DataFrame to a CSV file
    #df.to_csv(args.output, index=False)  # `index=False` avoids writing row numbers

    # ===== 新增:额外生成"近邻方向"yes/no 题 =====
    neighbor_questions = []
    for triple in sampled_triples:
        q, t, dist = generate_neighbor_yesno_question(triple, steps=args.steps)   # ← 改:接 3 个
        if q is not None:
            neighbor_questions.append((q, t, dist))                              # ← 改:存 3 个

    df_neighbor = pd.DataFrame(neighbor_questions,
                               columns=["query", "truth", "angular_distance"])    # ← 改:3 列
    df_neighbor.to_csv(args.neighbor_output, index=False)

    n_yes = sum(1 for q, t, d in neighbor_questions if t == "yes")               # ← 改:解包 3 个
    n_no = len(neighbor_questions) - n_yes
    print(f"[neighbor] wrote {len(neighbor_questions)} questions (yes={n_yes}, no={n_no})")
if __name__ == "__main__":
    main()