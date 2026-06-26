import re, argparse
import pandas as pd

CYCLE = ['north','northeast','east','southeast','south','southwest','west','northwest']
TOPO_NEIGHBORS = {
    frozenset(['intersects with','contains']): 0.5,
    frozenset(['intersects with','inside']):   0.5,
}

def parse_options(query):
    m = re.search(r'Options:\s*(.*)$', str(query))
    if not m: return {}
    pairs = re.findall(r'([a-e])\.\s*(.*?)(?=\s+[a-e]\.\s|$)', m.group(1))
    return {l: t.strip().rstrip('.').lower() for l, t in pairs}

def normalize(rel):
    rel = rel.strip().lower()
    adj = rel.startswith('adjacent to and ')#.startswith(X) 检查字符串是不是以 X 开头,返回 True 或 False。
    core = rel.replace('adjacent to and ', '').removesuffix(' of').strip()
    return adj, core

def graded_score(rel_true, rel_pred, decay=0.5, adj_penalty=0.5):
    if rel_true == rel_pred: return 1.0
    a_t, c_t = normalize(rel_true); a_p, c_p = normalize(rel_pred)
    if c_t == 'none of the above' or c_p == 'none of the above': return 0.0
    if c_t in CYCLE and c_p in CYCLE:
        d = abs(CYCLE.index(c_t) - CYCLE.index(c_p)); d = min(d, 8 - d)
        base = max(0.0, 1.0 - d * decay)
        return base * (1.0 if a_t == a_p else adj_penalty)# if the real relation and the result of SPaRAG have the same reponse for 'adjacent to' , we use the coefficient 1 * base, else even though they have the same result for the direction, we should reduce the coefficient for 0.5
    return TOPO_NEIGHBORS.get(frozenset([c_t, c_p]), 0.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-response_path', required=True)
    ap.add_argument('-decay', type=float, default=0.5)
    ap.add_argument('-adj_penalty', type=float, default=0.5)
    args = ap.parse_args()
    df = pd.read_csv(args.response_path)
    n=strict=graded=invalid=0; ex=[]


    for _, row in df.iterrows():#df.iterrows() 逐行遍历表格,每次给出行号和该行内容。这里行号用 _, row 是当前这道题(含 query、truth、response)。
        opts = parse_options(row['query'])
        t = str(row['truth']).strip().rstrip('.'); p = str(row['response']).strip().rstrip('.')
        n += 1
        if t not in opts or p not in opts: invalid += 1; continue
        s = graded_score(opts[t], opts[p], args.decay, args.adj_penalty) # score approximate
        st = 1.0 if t == p else 0.0  # score strict
        strict += st; graded += s
        if st == 0 and s > 0 and len(ex) < 5: ex.append((opts[t], opts[p], round(s,2)))#它的作用是:专门挑出那些"严格评分判错、但分级评分给了部分分"的题(也就是'答得接近但不完全对'的题),收集几个当例子展示给你看。some examples for the difference between s and st, we need only five examples
    # print(f"题数: {n}  (无法识别: {invalid})")
    # print(f"严格准确率 (0/1):        {strict/n:.3f}")
    # print(f"概念邻域分级得分 (新):    {graded/n:.3f}")
    # print(f"差值 (部分分):           +{(graded-strict)/n:.3f}")
    # if ex:
    #     print("\n部分分例子 (真值|预测|分):")
    print(f"Total questions: {n}  (unrecognized: {invalid})")
    print(f"Strict accuracy (0/1):           {strict/n:.3f}")
    print(f"Conceptual-neighbourhood score:  {graded/n:.3f}")
    print(f"Difference (partial credit):     +{(graded-strict)/n:.3f}")#.3f —— 保留 3 位小数
    if ex:
        print("\nPartial-credit examples (truth | prediction | score):")
        for t,p,s in ex: print(f"  {t} | {p} | {s}")
    

if __name__ == "__main__":
    main()
