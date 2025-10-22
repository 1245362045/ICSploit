import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
import itertools
import numpy as np
from Levenshtein import ratio
from sklearn.metrics import completeness_score, homogeneity_score
import storage
import function
# 合并静态字段
def merged_fields(schema):
    schema_dict = OrderedDict()
    length = max(len(elem) for elem in schema)  # 确定数据最大长度
    for index in range(0, length, 2):  # 以一个字节为单位遍历
        temp_list = [el[index: index + 2] for el in schema if len(el) > index]
        if index > 0:
            schema_list = list(schema_dict.items())  # 将键值对分割为一个个子列表存储在列表中[序号，['元素',字长,相似度,索引]]
            prev_entry = schema_list[-1]  # 获取上一个元素的信息（子列表信息）
        else:
            prev_entry = None

        if prev_entry == None:  # 如果是第一个元素
            if len(set(temp_list)) > 1:  # 如果是动态字段则存储格式为【第一个子列表第一个元素，字长，动态字段，相似度，索引】
                schema_dict[1] = [temp_list[0], 2, "Dynamic", LevenshteinSimilarityScore(temp_list), index]
            else:  # 如果是静态字段则存储格式为【第一个子列表元素、字长、静态字段、索引】
                schema_dict[1] = [temp_list[0], 2, "Static", 1, index]

        elif len(set(temp_list)) > 1:  # 动态字段按字节存储，元素取最后一个
            schema_dict[int(prev_entry[0]) + 1] = [temp_list[-1], 2, "Dynamic", LevenshteinSimilarityScore(temp_list), index]

        elif len(set(temp_list)) == 1 and prev_entry[1][2] == "Static":  # 合并静态字段
            temp_list = [prev_entry[1][0] + temp_list[0]]
            schema_dict[int(prev_entry[0])] = [temp_list[0], int(prev_entry[1][1]) + 2, "Static", 1, prev_entry[1][4]]

        elif len(set(temp_list)) == 1:  # 静态字段按字节存储
            schema_dict[int(prev_entry[0]) + 1] = [temp_list[0], 2, "Static", 1, index]

    return schema_dict  # 返回构成字段信息的有序字典

# 相似度分数
def LevenshteinSimilarityScore(value_list):
    SimilarityScore = []
    combination_list = list(itertools.combinations(value_list, 2))  # 生成所有可能的两两组合列表
    for each_com in combination_list:
        SimilarityScore.append(ratio(each_com[0], each_com[1]))
    SimilarityScore = np.array(SimilarityScore)
    if len(SimilarityScore) == 0:
        return 0
    return SimilarityScore.mean()

# 筛选可能的关键字段（0.6-0.9）
def get_probable_keyword_bytes(schema):
    # Control values of M
    keywords_list = []
    min_range = float(0.6)
    max_range = float(0.9)
    iteration = 1
    while max_range <= 1.0:
        for el in schema:
            val = schema.get(el)
            if int(val[4]) < min_len and val[2] == "Dynamic":
                # for i, el in enumerate(val[3]):
                if val[3] > min_range and val[3] < max_range:
                    keywords_list.append([int(val[4]), int(val[1]), val[3]])
        if len(keywords_list) > 0:
            return keywords_list
        else:
            iteration += 1
            max_range += 0.1
            print("Updating range for round", iteration, "\n New range : \tmin_value = ", min_range, " \tmax_value = ",
                  max_range)

    # print(keywords_list)

    while min_range >= 0.40:
        for el in schema:
            val = schema.get(el)
            if int(val[4]) < min_len and val[2] == "Dynamic":
                if val[3] > min_range and val[3] < max_range:
                    keywords_list.append([int(val[4]), int(val[1]), val[3]]) #关键字段列表（索引，长度，相似度）
        if len(keywords_list) > 0:
            return keywords_list
        else:
            iteration += 1
            min_range -= 0.1
            print("Updating range for round", iteration, "\n New range : \tmin_value = ", min_range, " \tmax_value = ",
                  max_range)
    return keywords_list  # 找出可能的关键字段列表

def generate_schema_for_keyfield(final_cluster):
    final_schema = {}
    for el in final_cluster:
        final_schema[el] = merged_fields(final_cluster.get(el))
    return final_schema


def generate_similarity_matrix(schema):
    LevenshteinList = []
    combination_list = list(itertools.combinations(schema, 2))
    for each_com in combination_list:
        LevenshteinList.append([each_com[0], each_com[1], ratio(each_com[0], each_com[1])])
    return LevenshteinList


def get_inter_intra_score(value_list):
    set_value_list = set(value_list)
    inter_score = []
    intra_score = []
    for el in similarity_matrix:
        if el[0] in set_value_list and el[1] in set_value_list:
            intra_score.append(el[2])
        elif el[0] in set_value_list or el[1] in set_value_list:
            inter_score.append(el[2])
    inter_score = np.array(inter_score)
    intra_score = np.array(intra_score)
    return inter_score.mean(), intra_score.mean()


def get_length_variance(value_list):
    total_len = 0
    for el in value_list:
        total_len += len(el)
    avg_len = total_len / len(value_list)
    max_len = len(max(value_list, key=len))
    return avg_len / max_len  # 平均长度和最大长度的比例

def cluster_for_field(keyfield, schema):#keyfield
    keyfield_schema = {}
    # print (keyfield)
    for el in schema:
        key = el[keyfield[0]: keyfield[0] + keyfield[1]] #得到是关键字段所在的值
        # print("el: ", el, " key: ", key)
        if key in keyfield_schema:
            val = keyfield_schema.get(key)  #获得所有该键对应的值
            val.append(el)                  #添加新值
            keyfield_schema[key] = val      #把新的值加入字典对应的关键字中
        else:
            keyfield_schema[key] = [el]
    return keyfield_schema

#判断列表，为了应对多请求单响应、单请求多响应、多请求多响应
def check_list(lst):
    list=[]
    if len(lst)<3:  #长度小于3
        return False
    elif len(set(lst))==1:  #只有一种类型
        return False
    else:
        for i in range(len(lst) - 1):
            if lst[i] != lst[i + 1]:  #获得后续不同的切片
                list=lst[i+1:]
                break
        # print(list)
        if len(set(list))==1:
            return False
        else:
            return True

def determine_protocol(pdml_file):
    for event, packet in ET.iterparse(pdml_file, events=('start',)):
        if packet.tag == 'proto':
            if 'name' in packet.attrib and packet.attrib['name'] == 'tcp' :
                print(f"The protocol in {pdml_file} is based on TCP.")
                return 'TCP'
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp' :
                print(f"The protocol in {pdml_file} is based on UDP.")
                return 'UDP'
    else:
        print(f"Failed to parse {pdml_file}.")

#数据预处理
def payload_filter(file_name, port):
    port = str(port)  # modbus502

    schema_request = []
    schema_response = []
    requests = []
    responses = []

    req = False
    resp = False

    list = []
    sequence_number = 1

    protocol = determine_protocol(file_name)
    if protocol == 'TCP':
        for event, packet in ET.iterparse(file_name, events=('start',)):
            if packet.tag == 'field':
                # print("Packet: ", packet.attrib['name']) if 'name' in packet.attrib else print("")
                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.srcport' and packet.attrib['show'] == port:
                    req = False
                    resp = True

                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.dstport' and packet.attrib['show'] == port:
                    # print("Found request packet")
                    req = True
                    resp = False

                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.payload':
                    if req:
                        list.append('q')
                        schema_request.append(packet.attrib['value'])

                        if check_list(list):
                            sequence_number+=1
                            requests.append([str(packet.attrib['value']), sequence_number])
                            list=list[-1:]
                        else:
                            requests.append([str(packet.attrib['value']), sequence_number])
                    elif resp:
                        list.append('p')
                        schema_response.append(packet.attrib['value'])

                        if check_list(list):
                            sequence_number += 1
                            responses.append([str(packet.attrib['value']), sequence_number])
                            list=list[-1:]
                        else:
                            responses.append([str(packet.attrib['value']), sequence_number])

                    req = False
                    resp = False

    if protocol == 'UDP':
        for event, packet in ET.iterparse(file_name, events=('start',)):
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.srcport' and packet.attrib['show'] == port:
                req = False
                resp = True
                sequence_number += 1
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.dstport' and packet.attrib['show'] == port:
                req = True
                resp = False
                sequence_number += 1
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.payload':
                if req:
                    list.append('q')
                    schema_request.append(packet.attrib['value'])

                    if check_list(list):
                        sequence_number += 1
                        requests.append([str(packet.attrib['value']), sequence_number])
                        list = list[-1:]
                    else:
                        requests.append([str(packet.attrib['value']), sequence_number])
                elif resp:
                    list.append('p')
                    schema_response.append(packet.attrib['value'])

                    if check_list(list):
                        sequence_number += 1
                        responses.append([str(packet.attrib['value']), sequence_number])
                        list = list[-1:]
                    else:
                        responses.append([str(packet.attrib['value']), sequence_number])
                req = False
                resp = False
    return schema_request, schema_response, requests, responses

#识别关键字段
def get_final_keyword_field(schema):
    final_similarity = []
    sequence_request =[]
    sequence_response =[]
    group_score=0
    num_key = 0
    num_keyvalue = []
    num_deviation=[]
    for keyfield in probable_key_fields:
        print("\nComputing probability for keyfield: ", keyfield)
        rqs_inter_score_array = []
        rqs_intra_score_array = []
        rqs_len_variance_array = []
        each_schema = cluster_for_field(keyfield, schema)
        each_rspschema =cluster_for_field(keyfield,schema_response)
        # print(each_schema)
        for key in each_schema:   #对每个关键字对应值的列表进行遍历
            num_key+=1
            num_keyvalue.append(len(each_schema.get(key)))
            print("\tParsing key: ", key)
            if len(each_schema.get(key)) < 2:
                print("\t\t Key with only one pacekt in cluster ....")
                rqs_inter_score_array.append(0)
                rqs_intra_score_array.append(0)
                rqs_len_variance_array.append(0)
                # continue
            else:
                print("\t\t Total number of packets in cluster = ", len(each_schema.get(key)))
                rqs_inter_score, rqs_intra_score = get_inter_intra_score(each_schema.get(key))
                rqs_len_variance = get_length_variance(each_schema.get(key))
                rqs_inter_score_array.append(rqs_inter_score)
                rqs_intra_score_array.append(rqs_intra_score)
                rqs_len_variance_array.append(rqs_len_variance)
                #寻找耦合序列对
                # print("请求报文的序列对；")
                for el in each_schema.get(key):
                  # print(el)
                  for enum in requests:
                      if el == enum[0]:
                          # print(enum[1])
                          sequence_request.append([el,enum[1],key])
                          sequence_request = sorted(sequence_request, key=lambda x: x[1])
                # print(sequence_request)
        #找响应的序列对
        for key in each_rspschema:
            for el in each_rspschema.get(key):
                # print(el)
                for enum in responses:
                    if el == enum[0]:
                        # print(enum[1])
                        sequence_response.append([el, enum[1], key])
                        sequence_response = sorted(sequence_response, key=lambda x: x[1])
            #print(sequence_response)
        sequence_pair = [[req[2], resp[2]] for req in sequence_request for resp in sequence_response if req[1] == resp[1]]
        num_pair=len(sequence_pair)
        print('耦合对总数：',{num_pair})
        unique_set = set(tuple(sublist) for sublist in sequence_pair)
        num_unique=len(unique_set)
        print('耦合对种类数：', {num_unique})
        if num_pair != 0:
            coupling_score = 1 - num_unique / num_pair
        else:
            coupling_score = 1
        # print(coupling_score)
        print('每个组元素的数量：',num_keyvalue)
        for el in num_keyvalue:
            num_deviation.append(abs(el-num_request/num_key))
            deviation=sum(num_deviation)
        print("每个组数量的偏差：", num_deviation)
        group_score=1-deviation/num_request

        print("\n\tStatistics for keyfield: ", keyfield)
        print("\t\tIntra score array : ", rqs_intra_score_array)
        print("\t\tLength variance array: ", rqs_len_variance_array)
        rqs_inter_score_array = np.array(rqs_inter_score_array)
        rqs_intra_score_array = np.array(rqs_intra_score_array)
        rqs_len_variance_array = np.array(rqs_len_variance_array)
        rqs_intra_score_mean = rqs_intra_score_array.mean() if len(rqs_intra_score_array) > 0 else 0
        rqs_inter_score_mean = rqs_inter_score_array.mean() if len(rqs_intra_score_array) > 0 else 1
        rqs_len_variance_mean = rqs_len_variance_array.mean() if len(rqs_len_variance_array) > 0 else 0
        print("\t\tInitial M value: ", keyfield[2])
        print("\t\tFinal group score:", group_score)
        print("\t\tFinal intra score: ", rqs_intra_score_mean)
        print("\t\tFinal inter score: ", rqs_inter_score_mean)
        print("\t\tFinal length variance: ", rqs_len_variance_mean)
        print('\t\tcoupling score:',coupling_score)
        # print("\t\tJoint Probability: ",
        #       keyfield[2] * rqs_intra_score_mean)  # * len_variance_mean) #* (1 - inter_score_mean))
        # print("\t\tFraction of clusters: ", (1 - (len(each_schema) / len(schema))))
        final_probability = rqs_inter_score_mean * rqs_intra_score_mean*rqs_len_variance_mean
        final_probability = final_probability * (1 - (len(each_schema) / len(schema)))+coupling_score*5+group_score*0.3
        print("\t\tFinal Probability: ", final_probability)
        final_similarity.append([keyfield[0], keyfield[1], final_probability])
        num_key=0
        num_keyvalue=[]
        group_score=0
        num_deviation = []
    print("\nProbabilty score for each keyfield: ", final_similarity)
    max_list = max(final_similarity, key=lambda sublist: sublist[2])
    return max_list

#打标签，方便求解同质性、完整性
def generate_labels(input_list,index,step):
    # 用于存储结果的标签列表
    labels = []
    # 用于存储已存在的子串及其对应标签的字典
    substring_to_label = {}
    # 当前可以使用的标签数字
    current_label = 0

    for element in input_list:
        if len(element) < index+step:
            raise ValueError("列表中的字符串长度不足")
        # 提取第1位到第3位的子串
        substring = element[index:index+step]
        # 检查这个子串是否已经有一个标签
        if substring in substring_to_label:
            # 如果有，则使用已有的标签
            label = substring_to_label[substring]
        else:
            # 如果没有，则分配一个新的标签
            label = current_label
            substring_to_label[substring] = label
            current_label += 1
        labels.append(label)
    return labels

# 文件数据读取
schema_request_list = OrderedDict()
schema_response_list = {}

schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/modbus_100.pdml",502) #（14，2）可以识别
# schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/s7_100.pdml",102)  #（34，2）可以识别
# schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/dnp3_100.pdml",20000) #（24，2）
# schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/dhcp_100.pdml",67)   #(484,2)可以识别
# schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/tftp_100.pdml",1024)  #(0,4)可以识别
# schema_request,schema_response,requests,responses=payload_filter("netplier_dataset/ntp_100.pdml",123) #(0,2)识别有误
# print(schema_request)  #输出请求列表
# print(schema_response) #输出响应列表
# print('请求报文：',requests)
# print('响应报文',responses)

num_request=len(schema_request)
print("请求报文总数量：",num_request)

with open('Protocol format.txt', 'w') as file:  #清空文件夹
    pass

key_reqlist=[]
key_rsp= {}
key_rsplist= []
#请求报文解析
if len(schema_request) != 0 :
    min_len = len(min(schema_request, key=len))
    print("Minimum payload length for request: ", min_len / 2, " bytes")

    schema_request_list = merged_fields(schema_request)

    for el in schema_request_list:
        print("Field no: ", el, " Field length: ", schema_request_list.get(el)[1], " Field Type: ",
              schema_request_list.get(el)[2], " M-score: ", schema_request_list.get(el)[3], " Index position: ",
              schema_request_list.get(el)[4])
        if schema_request_list.get(el)[3]>=0.6:
            storage.append_to_file('Protocol format.txt','不变字段',schema_request_list.get(el)[4],schema_request_list.get(el)[1])

    # print("\nGenerating similarity matrix...")
    similarity_matrix = generate_similarity_matrix(schema_request)
    probable_key_fields = get_probable_keyword_bytes(schema_request_list)
    #获得关键字的值
    print("\nProbable reqKeyfields : ", probable_key_fields)

    if len(probable_key_fields) == 0:
        sys.exit("\nPlease add more input packets.... No keyfield found. \nExiting....")

if len(schema_response) !=0 :
    #响应报文解析：
    min_len = len(min(schema_response, key=len))
    print("Minimum payload length for response: ", min_len / 2, " bytes")

    schema_response_list =  merged_fields(schema_response)

    for el in schema_response_list:
        print("Field no: ", el, " Field length: ", schema_response_list.get(el)[1], " Field Type: ",
              schema_response_list.get(el)[2], " M-score: ", schema_response_list.get(el)[3], " Index position: ",
              schema_response_list.get(el)[4])

    # print("\nGenerating similarity matrix...")
    similarity_rspmatrix = generate_similarity_matrix(schema_response)
    probable_rspkey_fields = get_probable_keyword_bytes(schema_response_list)
    print("\nProbable rspKeyfields : ", probable_rspkey_fields)
    #获得响应关键字可能的值存储到字典中
    for keyfield in probable_rspkey_fields:
        key_rsp[keyfield[0]]=set([message[keyfield[0]:keyfield[0]+keyfield[1]] for message in schema_response])
    print('key probable rspvalue:',key_rsp)





keyword_final = get_final_keyword_field(schema_request)
print("\nreqKeyword Final : ", keyword_final)
storage.append_to_file('Protocol format.txt','请求关键字段',keyword_final[0],keyword_final[1])

key_reqlist=set([message[keyword_final[0]:keyword_final[0]+keyword_final[1]] for message in schema_request])
print('key value:',key_reqlist)



#求完整性，同质性
true_labels=generate_labels(schema_request,14,2)
predict_labels=generate_labels(schema_request,keyword_final[0],keyword_final[1])
completeness = completeness_score(true_labels, predict_labels)
homogeneity = homogeneity_score(true_labels, predict_labels)
V_measure = 2 * ((completeness * homogeneity)/(completeness + homogeneity))
print(f'完整性: {completeness}')
print(f'同质性: {homogeneity}')
print(f'V_measure: {V_measure}')



final_cluster = cluster_for_field(keyword_final, schema_request)

final_schema = generate_schema_for_keyfield(final_cluster)


print("\nFinal Grammar for request: ")
fcode_dict={}
for el in final_schema:
    print("Protocol function : ", el)
    val = final_schema.get(el)
    if el not in fcode_dict:
        fcode_dict[el] = []
    for key in val:
        print("\t key: ", key, " val: ", val.get(key))
        fcode_dict[el].append(val.get(key)[1:4])



#确定响应报文的关键字
for key in key_rsp:
    if key_rsp[key]==key_reqlist:
        keyword_final=[key,2]
print('\nresponse keyword_final',keyword_final)
storage.append_to_file('Protocol format.txt','响应关键字段',keyword_final[0],keyword_final[1])


if len(schema_response) != 0:
    final_cluster = cluster_for_field(keyword_final, schema_response)
    final_schema = generate_schema_for_keyfield(final_cluster)

    print("\nFinal Grammar for response: ")

    for el in final_schema:
        print("Protocol function : ", el)
        val = final_schema.get(el)
        for key in val:
            print("\t key: ", key, " val: ", val.get(key))

function.write_dict_to_txt(fcode_dict)