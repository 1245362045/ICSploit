import networkx as nx
import matplotlib.pyplot as plt




def read_list_from_file(filename):
    # 创建一个空字典来存储结果
    result_list = []

    # 打开文件
    with open(filename, 'r') as file:
        # 遍历文件的每一行
        for line in file:
            # 去除行尾的换行符
            line = line.strip()
            result_list.append(line)
    return result_list


function_code_pairs=[]
Function_list = read_list_from_file('fuzzing/modbus_System status tracking.txt')
for list in Function_list:

    # print([list[2:4],list[8:10]])
    function_code_pairs.append([list[2:4],list[8:10]])
# print(state_machine)




# 创建一个有向图
G = nx.DiGraph()

# 添加节点和边，条件是前一个响应功能码值与下一个请求功能码值相同
for i in range(len(function_code_pairs) - 1):
    req1, resp1 = function_code_pairs[i]
    req2, resp2 = function_code_pairs[i + 1]

    # 添加当前点
    G.add_node(f'{req1},{resp1}')

    # 如果前一个响应功能码值和后一个请求功能码值相同，添加边
    if resp1 == req2:
        G.add_edge(f'{req1},{resp1}', f'{req2},{resp2}')

# 最后一个点也要加上
last_pair = function_code_pairs[-1]
G.add_node(f'{last_pair[0]},{last_pair[1]}')

# 绘制图
plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G)  # 设置节点的布局
nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=3000, font_size=10, font_weight='bold',
        edge_color='gray')

# 显示图形
plt.title("协议状态机图")
plt.show()
